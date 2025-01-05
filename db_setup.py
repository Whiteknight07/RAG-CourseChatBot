from dotenv import load_dotenv
import os
import pandas as pd
from langchain_community.graphs import Neo4jGraph
from langchain_openai import OpenAIEmbeddings

# Load environment variables
load_dotenv('.env', override=True)
NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
NEO4J_DATABASE = os.getenv('NEO4J_DATABASE')
OPENAI_API_KEY = os.getenv('OPENAIAPIKEY')

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

def prepare_course_params(row):
    """Prepare course parameters for Neo4j"""
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

def update_embeddings(kg, embeddings):
    """Create embeddings for courses that don't have them"""
    embedding_query = """
    MATCH (course:Course) 
    WHERE course.embedding IS NULL 
    AND course.description IS NOT NULL 
    AND course.description <> ''
    RETURN course.courseCode AS courseCode, course.description AS description
    """
    
    courses_to_embed = kg.query(embedding_query)
    success_count = 0
    
    for course in courses_to_embed:
        description = course['description']
        # Skip if description is not a string or is empty
        if not isinstance(description, str) or not description.strip():
            print(f"Skipping {course['courseCode']}: Invalid or empty description")
            continue
            
        try:
            embedding_vector = embeddings.embed_query(description)
            kg.query(
                """
                MATCH (course:Course {courseCode: $courseCode})
                SET course.embedding = $embedding
                """,
                params={
                    "courseCode": course['courseCode'],
                    "embedding": embedding_vector
                }
            )
            success_count += 1
            print(f"Created embedding for {course['courseCode']}")
        except Exception as e:
            print(f"Error creating embedding for {course['courseCode']}: {e}")
    
    return success_count

def setup_database():
    """Initialize the Neo4j database with course data and embeddings"""
    try:
        # Connect to Neo4j
        print("Connecting to Neo4j...")
        kg = Neo4jGraph(
            url=NEO4J_URI, 
            username=NEO4J_USERNAME, 
            password=NEO4J_PASSWORD, 
            database=NEO4J_DATABASE
        )

        # Create vector index
        print("Creating vector index...")
        kg.query("""
            CREATE VECTOR INDEX course_embeddings IF NOT EXISTS
            FOR (c:Course) ON (c.embedding)
            OPTIONS { indexConfig: {
                `vector.dimensions`: 1536,
                `vector.similarity_function`: 'cosine'
            }}
        """)

        # Load and process CSV
        print("Loading course data...")
        csv_path = os.path.join(os.path.dirname(__file__), 'courses_info copy.csv')
        courses_df = pd.read_csv(csv_path)

        # Create course nodes and relationships
        print("Creating course nodes and relationships...")
        for _, row in courses_df.iterrows():
            course_data = prepare_course_params(row)
            kg.query(merge_course_node_query, params={"courseParam": course_data})

        # Initialize embeddings
        print("Initializing OpenAI embeddings...")
        embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
        
        # Create embeddings for courses without them
        print("Creating course embeddings...")
        num_embeddings = update_embeddings(kg, embeddings)
        print(f"Created embeddings for {num_embeddings} courses")

        print("Database setup complete!")
        
    except Exception as e:
        print(f"Error during database setup: {e}")
        if 'kg' in locals():
            print("Attempting to refresh schema...")
            kg.refresh_schema()
        raise

if __name__ == "__main__":
    setup_database()
