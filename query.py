from dotenv import load_dotenv
import os
from langchain_community.graphs import Neo4jGraph
from langchain_openai import OpenAIEmbeddings

# Load environment variables
load_dotenv('.env', override=True)
NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
NEO4J_DATABASE = os.getenv('NEO4J_DATABASE')
OPENAI_API_KEY = os.getenv('OPENAIAPIKEY')

class CourseQuery:
    def __init__(self):
        self.kg = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE
        )
        self.embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    def search_courses(self, question, top_k=2):  # Changed default to 2
        """
        Search for similar course nodes using the Neo4j vector index
        Args:
            question: search query text
            top_k: number of similar results to return (default: 2)
        Returns:
            List of similar courses with their similarity scores
        """
        question_embedding = self.embeddings.embed_query(question)
        
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
        
        return self.kg.query(
            vector_search_query,
            params={
                'embedding': question_embedding,
                'top_k': top_k
            }
        )

    def display_results(self, results):
        """Display search results in a formatted way"""
        for result in results:
            print(f"Score: {result['score']}")
            print(f"Course: {result['courseCode']} - {result['name']}")
            print(f"Description: {result['description']}\n")

def main():
    querier = CourseQuery()
    while True:
        question = input("\nEnter your question (or 'quit' to exit): ")
        if question.lower() == 'quit':
            break
        
        try:
            num_results = int(input("How many results do you want? (default: 2) ") or 2)
        except ValueError:
            num_results = 2
            
        results = querier.search_courses(question, top_k=num_results)
        querier.display_results(results)

if __name__ == "__main__":
    main()
