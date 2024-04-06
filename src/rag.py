from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain.schema.output_parser import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import PromptTemplate
from langchain import hub
from langchain.vectorstores.utils import filter_complex_metadata
from langchain import hub
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory

class ChatPDF:
    vector_store = None
    retriever = None
    chain = None
    
    def __init__(self):
        self.model = ChatOllama(model="llama2")
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=100, add_start_index=True)
        self.prompt = PromptTemplate.from_template(
            """
            You're a helpful AI assistant. You are a teaching assistant for the course of programming languages. You will only provide relevant answers to the question Use the following pieces of context to answer the question at the end.
            If you don't know the answer, just say that you don't know, don't try to make up an answer.
            Use three sentences maximum and keep the answer as concise as possible. You also know how to speak in Romanian.
            Always say "thanks for asking!" at the end of the answer. Remember, you must return both an answer and citations. A citation consists of a VERBATIM quote that justifies the answer and the ID of the quote article. Return a citation for every quote across all articles \
            that justify the answer. Use the following format for your final output:

            <cited_answer>
                <answer></answer>
                <citations>
                    <citation><source_id></source_id><quote></quote></citation>
                    <citation><source_id></source_id><quote></quote></citation>
                    ...
                </citations>
            </cited_answer>
            Question: {question} 
            Context: {context} 
            Answer:
            """
        )

    def ingest(self, pdf_file_path: str):
        docs = PyPDFLoader(file_path=pdf_file_path).load()
        chunks = self.text_splitter.split_documents(docs)
        chunks = filter_complex_metadata(chunks)

        vector_store = Chroma.from_documents(documents=chunks, embedding=FastEmbedEmbeddings())
        self.retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": 10,
            },
        )
        prompt = hub.pull("rlm/rag-prompt")
        print("DEBUG: retriever", self.retriever)
        self.chain = ({"context": self.retriever, "question": RunnablePassthrough()}
                      | prompt
                      | self.model
                      | StrOutputParser())
        contextualize_q_system_prompt = """Given a chat history and the latest user question \
        which might reference context in the chat history, formulate a standalone question \
        which can be understood without the chat history. Do NOT answer the question, \
        just reformulate it if needed and otherwise return it as is."""
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        history_aware_retriever = create_history_aware_retriever(
            self.model, self.retriever, contextualize_q_prompt
        )
        ### Answer question ###
        qa_system_prompt = """You are an assistant for question-answering tasks. \
        Use the following pieces of retrieved context to answer the question. \
        If you don't know the answer, just say that you don't know. \
        Use three sentences maximum and keep the answer concise.\

        {context}"""
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qa_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        question_answer_chain = create_stuff_documents_chain(self.model, qa_prompt)
        
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
        store = {}
        def get_session_history(session_id):
            if session_id not in store:
                store[session_id] = ChatMessageHistory()
            return store[session_id]


        self.conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

    def ask(self, query: str):
        if not self.chain:
            return "Please, add a PDF document first."
        return self.conversational_rag_chain.invoke(
                        {"input": query},
                        config={
                            "configurable": {"session_id": "abc123"}
                        },
                    )["answer"]

    def clear(self):
        self.vector_store = None
        self.retriever = None
        self.chain = None