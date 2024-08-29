from typing import List, Optional
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableParallel
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_mistralai import ChatMistralAI
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_fireworks import ChatFireworks
from langchain_google_vertexai import ChatVertexAI
from langchain_community.chat_models import ChatOllama
from tqdm import tqdm
from ..utils.logging import get_logger
from .base_node import BaseNode
from ..prompts import TEMPLATE_CHUNKS, TEMPLATE_NO_CHUNKS, TEMPLATE_MERGE, TEMPLATE_CHUNKS_MD, TEMPLATE_NO_CHUNKS_MD, \
    TEMPLATE_MERGE_MD


class GenerateAnswerNode(BaseNode):
    """
    A node that generates an answer using a large language model (LLM) based on the user's input
    and the content extracted from a webpage. It constructs a prompt from the user's input
    and the scraped content, feeds it to the LLM, and parses the LLM's response to produce
    an answer.

    Attributes:
        llm_model: An instance of a language model client, configured for generating answers.
        verbose (bool): A flag indicating whether to show print statements during execution.

    Args:
        input (str): Boolean expression defining the input keys needed from the state.
        output (List[str]): List of output keys to be updated in the state.
        node_config (dict): Additional configuration for the node.
        node_name (str): The unique identifier name for the node, defaulting to "GenerateAnswer".
    """

    def __init__(
            self,
            input: str,
            output: List[str],
            node_config: Optional[dict] = None,
            node_name: str = "GenerateAnswer",
    ):
        super().__init__(node_name, "node", input, output, 2, node_config)

        self.llm_model = node_config["llm_model"]

        if isinstance(node_config["llm_model"], ChatOllama):
            self.llm_model.format = "json"

        self.verbose = (
            True if node_config is None else node_config.get("verbose", False)
        )
        self.force = (
            False if node_config is None else node_config.get("force", False)
        )
        self.script_creator = (
            False if node_config is None else node_config.get("script_creator", False)
        )
        self.is_md_scraper = (
            False if node_config is None else node_config.get("is_md_scraper", False)
        )

        self.additional_info = node_config.get("additional_info")

    def execute(self, state: dict) -> dict:
        """
        Generates an answer by constructing a prompt from the user's input and the scraped
        content, querying the language model, and parsing its response.

        Args:
            state (dict): The current state of the graph. The input keys will be used
                            to fetch the correct data from the state.

        Returns:
            dict: The updated state with the output key containing the generated answer.

        Raises:
            KeyError: If the input keys are not found in the state, indicating
                      that the necessary information for generating an answer is missing.
        """

        self.logger.info(f"--- Executing {self.node_name} Node ---")

        # Interpret input keys based on the provided input expression
        input_keys = self.get_input_keys(state)
        # Fetching data from the state based on the input keys
        input_data = [state[key] for key in input_keys]
        user_prompt = input_data[0]
        doc = input_data[1]

        # Initialize the output parser
        if self.node_config.get("schema", None) is not None:
            output_parser = JsonOutputParser(pydantic_object=self.node_config["schema"])

            # Use built-in structured output for providers that allow it
            if isinstance(self.llm_model,
                          (ChatOpenAI, ChatMistralAI, ChatAnthropic, ChatFireworks, ChatGroq, ChatVertexAI)):
                self.llm_model = self.llm_model.with_structured_output(
                    schema=self.node_config["schema"],
                    method="json_schema")

        else:
            output_parser = JsonOutputParser()

        format_instructions = output_parser.get_format_instructions()

        if isinstance(self.llm_model, (ChatOpenAI,
                                       AzureChatOpenAI)) and not self.script_creator or self.force and not self.script_creator or self.is_md_scraper:
            template_no_chunks_prompt = TEMPLATE_NO_CHUNKS_MD
            template_chunks_prompt = TEMPLATE_CHUNKS_MD
            template_merge_prompt = TEMPLATE_MERGE_MD
        else:
            template_no_chunks_prompt = TEMPLATE_NO_CHUNKS
            template_chunks_prompt = TEMPLATE_CHUNKS
            template_merge_prompt = TEMPLATE_MERGE

        if self.additional_info is not None:
            template_no_chunks_prompt = self.additional_info + template_no_chunks_prompt
            template_chunks_prompt = self.additional_info + template_chunks_prompt
            template_merge_prompt = self.additional_info + template_merge_prompt

        if len(doc) == 1:
            prompt = PromptTemplate(
                template=template_no_chunks_prompt,
                input_variables=["question"],
                partial_variables={"context": doc,
                                   "format_instructions": format_instructions})
            chain = prompt | self.llm_model | output_parser
            answer = chain.invoke({"question": user_prompt})

            state.update({self.output[0]: answer})
            return state

        chains_dict = {}
        for i, chunk in enumerate(tqdm(doc, desc="Processing chunks", disable=not self.verbose)):
            prompt = PromptTemplate(
                template=TEMPLATE_CHUNKS,
                input_variables=["question"],
                partial_variables={"context": chunk,
                                   "chunk_id": i + 1,
                                   "format_instructions": format_instructions})
            chain_name = f"chunk{i + 1}"
            chains_dict[chain_name] = prompt | self.llm_model | output_parser

        async_runner = RunnableParallel(**chains_dict)

        batch_results = async_runner.invoke({"question": user_prompt})

        merge_prompt = PromptTemplate(
            template=template_merge_prompt,
            input_variables=["context", "question"],
            partial_variables={"format_instructions": format_instructions},
        )

        merge_chain = merge_prompt | self.llm_model | output_parser
        answer = merge_chain.invoke({"context": batch_results, "question": user_prompt})

        state.update({self.output[0]: answer})
        return state
