from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_community.docstore.document import Document
import pandas as pd


# Load your local LLM
llm = OllamaLLM(model="tinyllama")

# Load dealer data
df = pd.read_csv("dealer_sales_mock.csv")
text_data = "\n".join(df.astype(str).apply(lambda x: ", ".join(x), axis=1))

#Split + embed data
splitter = CharacterTextSplitter(chunk_size=200, chunk_overlap=50)
chunks = splitter.split_text(text_data)

embeddings = OllamaEmbeddings(model="tinyllama")
vectordb = FAISS.from_texts(chunks, embedding=embeddings)

#Build a simple retrieval pipeline
retriever = vectordb.as_retriever(search_kwargs={"k": 3})

prompt = ChatPromptTemplate.from_template(
    "You are a helpful assistant analyzing dealer sales data.\n"
    "Use the context below to answer the question:\n\n{context}\n\n"
    "Question: {question}"
)

def get_context(inputs):
    docs = retriever.invoke(inputs["question"])
    return "\n\n".join([d.page_content for d in docs])

# RunnableSequence defines a mini-agent pipeline
qa_chain = RunnableSequence(
    {
        "context": get_context,
        "question": lambda x: x["question"],
    },
    prompt,
    llm
)

#Ask a question
query = "Which dealer has the lowest gmv_in_dollar?"
response = qa_chain.invoke({"question": query})

print("🤖:", response)
