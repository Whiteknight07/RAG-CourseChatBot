from dotenv import load_dotenv
import os

# Common data processing
import json
import textwrap
import pandas as pd

# Langchain
from langchain_community.graphs import Neo4jGraph
from langchain_community.vectorstores import Neo4jVector
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQAWithSourcesChain
from langchain_openai import ChatOpenAI

load_dotenv('.env', override=True)
NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
NEO4J_DATABASE = os.getenv('NEO4J_DATABASE')
OPENAI_API_KEY = os.getenv('OPENAIAPIKEY')

# Global constants
VECTOR_INDEX_NAME = 'form_10k_chunks'
VECTOR_NODE_LABEL = 'Chunk'
VECTOR_SOURCE_PROPERTY = 'text'
VECTOR_EMBEDDING_PROPERTY = 'textEmbedding'

# Load the CSV file using proper path handling
csv_path = os.path.join(os.path.dirname(__file__), 'courses_info copy.csv')
courses_df = pd.read_csv(csv_path)

# Configure the text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = 2000,
    chunk_overlap  = 200,
)

# Prepare the course documents for splitting by combining all relevant information
courses_texts = courses_df.apply(
    lambda x: f"""ID: {x['id']}
Course Code: {x['course_code']}
Campus: {x['campus']}
Year: {x['year']}
Name: {x['name']}
Description: {x['description']}
Credits: {x['credits']}
Honours: {x['is_honours']}
Restrictions: {x['restrictions']}
Equivalent Courses: {x['equivalent_string']}
Co-requisites: {x['co-req_string']}
Prerequisites: {x['pre-req_string']}
Equivalent Courses List: {x['courses_in_equivalent_string']}
Co-requisite Courses List: {x['courses_in_co-req_string']}
Prerequisite Courses List: {x['courses_in_pre-req_string']}
Winter Term 1: {x['winter_term_1']}
Winter Term 2: {x['winter_term_2']}
Summer Term 1: {x['summer_term_1']}
Summer Term 2: {x['summer_term_2']}
Duration Terms: {x['duration_terms//']}
Source: {x['source']}""",
    axis=1
).tolist()

# Split the texts
split_texts = text_splitter.create_documents(courses_texts)

# Neo4j Cypher query for creating course nodes and relationships
merge_course_node_query = """
MERGE (course:Course {courseCode: $courseParam.courseCode})
    ON CREATE SET 
        course.id = $courseParam.id,
        course.campus = $courseParam.campus,
        course.year = $courseParam.year,
        course.name = $courseParam.name,
        course.description = $courseParam.description,
        course.credits = $courseParam.credits,
        course.isHonours = $courseParam.isHonours,
        course.restrictions = $courseParam.restrictions,
        course.winterTerm1 = $courseParam.winterTerm1,
        course.winterTerm2 = $courseParam.winterTerm2,
        course.summerTerm1 = $courseParam.summerTerm1,
        course.summerTerm2 = $courseParam.summerTerm2,
        course.durationTerms = $courseParam.durationTerms

// Create prerequisite relationships
WITH course
UNWIND $courseParam.prerequisites AS prereq
MERGE (prereqCourse:Course {courseCode: prereq})
MERGE (prereqCourse)-[:PREREQ_OF]->(course)

// Create corequisite relationships
WITH course
UNWIND $courseParam.corequisites AS coreq
MERGE (coreqCourse:Course {courseCode: coreq})
MERGE (course)-[:COREQ_WITH]->(coreqCourse)

// Create equivalent course relationships
WITH course
UNWIND $courseParam.equivalents AS equiv
MERGE (equivCourse:Course {courseCode: equiv})
MERGE (course)-[:EQUIVALENT_TO]->(equivCourse)

RETURN course
"""

# Prepare course data for Neo4j
def prepare_course_params(row):
    return {
        "courseCode": row['course_code'],
        "id": row['id'],
        "campus": row['campus'],
        "year": row['year'],
        "name": row['name'],
        "description": row['description'],
        "credits": row['credits'],
        "isHonours": row['is_honours'],
        "restrictions": row['restrictions'],
        "winterTerm1": row['winter_term_1'],
        "winterTerm2": row['winter_term_2'],
        "summerTerm1": row['summer_term_1'],
        "summerTerm2": row['summer_term_2'],
        "durationTerms": row['duration_terms//'],
        "prerequisites": row['courses_in_pre-req_string'].split(',') if pd.notna(row['courses_in_pre-req_string']) else [],
        "corequisites": row['courses_in_co-req_string'].split(',') if pd.notna(row['courses_in_co-req_string']) else [],
        "equivalents": row['courses_in_equivalent_string'].split(',') if pd.notna(row['courses_in_equivalent_string']) else []
    }

#Set up connection to graph instance using LangChain use the connection details from .env file
kg = Neo4jGraph(
    url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD, database=NEO4J_DATABASE
)

# Create vector index for course embeddings
kg.query("""
    CREATE VECTOR INDEX course_embeddings IF NOT EXISTS
    FOR (c:Course) ON (c.embedding)
    OPTIONS { indexConfig: {
        `vector.dimensions`: 1536,
        `vector.similarity_function`: 'cosine'
    }}
""")

print("Vector index created successfully!")

# Create course nodes and relationships in Neo4j
for i, split_text in enumerate(split_texts):
    course_data = prepare_course_params(courses_df.iloc[i])
    kg.query(
        merge_course_node_query, 
        params={"courseParam": course_data}  # Wrap parameter in a params dictionary
    )

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

# Calculate embeddings for courses
def update_embeddings():
    embedding_query = """
    MATCH (course:Course) 
    WHERE course.embedding IS NULL AND course.description IS NOT NULL
    RETURN course.courseCode AS courseCode, course.description AS description
    """
    
    # Get courses needing embeddings
    courses_to_embed = kg.query(embedding_query)
    
    for course in courses_to_embed:
        if not course['description']:  # Skip if description is empty
            continue
            
        try:
            # Generate embedding using OpenAI
            embedding_vector = embeddings.embed_query(course['description'])
            
            # Update course node with embedding
            update_query = """
            MATCH (course:Course {courseCode: $courseCode})
            SET course.embedding = $embedding
            """
            
            kg.query(
                update_query,
                params={
                    "courseCode": course['courseCode'],
                    "embedding": embedding_vector
                }
            )
            print(f"Created embedding for {course['courseCode']}")
        except Exception as e:
            print(f"Error creating embedding for {course['courseCode']}: {e}")
    
    return len(courses_to_embed)

try:
    num_embeddings = update_embeddings()
    print(f"Created embeddings for {num_embeddings} courses")
except Exception as e:
    print(f"Error creating embeddings: {e}")
    print(f"Using API key: {'Present' if OPENAI_API_KEY else 'Missing'}")

print("Embeddings created successfully!")
kg.refresh_schema()

def neo4j_vector_search(question, top_k=10):
    """
    Search for similar course nodes using the Neo4j vector index
    Args:
        question: search query text
        top_k: number of similar results to return
    Returns:
        List of similar courses with their similarity scores
    """
    # Generate embedding for question
    question_embedding = embeddings.embed_query(question)
    
    vector_search_query = """
    CALL db.index.vector.queryNodes('course_embeddings', $top_k, $embedding) 
    YIELD node, score
    RETURN 
        score,
        node.courseCode AS courseCode,
        node.name AS name,
        node.description AS description
    ORDER BY score DESC
    """
    
    return kg.query(
        vector_search_query,
        params={
            'embedding': question_embedding,
            'top_k': top_k
        }
    )

# Example usage:
results = neo4j_vector_search("What is the teach machine learning?")
for result in results:
     print(f"Score: {result['score']}")
     print(f"Course: {result['courseCode']} - {result['name']}")
     print(f"Description: {result['description']}\n")



