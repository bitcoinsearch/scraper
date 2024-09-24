"""
SmartScraperGraph Module
"""

from typing import Optional
import logging
from pydantic import BaseModel
from scrapegraphai.graphs import BaseGraph
from scrapegraphai.graphs import AbstractGraph

from scrapegraphai.nodes import (
    FetchNode,
    ParseNode,
    GenerateAnswerNode
)


class CustomScraperGraph(AbstractGraph):
    """
    SmartScraper is a scraping pipeline that automates the process of 
    extracting information from web pages
    using a natural language model to interpret and answer prompts.

    Attributes:
        prompt (str): The prompt for the graph.
        source (str): The source of the graph.
        config (dict): Configuration parameters for the graph.
        schema (BaseModel): The schema for the graph output.
        llm_model: An instance of a language model client, configured for generating answers.
        embedder_model: An instance of an embedding model client, 
        configured for generating embeddings.
        verbose (bool): A flag indicating whether to show print statements during execution.
        headless (bool): A flag indicating whether to run the graph in headless mode.

    Args:
        prompt (str): The prompt for the graph.
        source (str): The source of the graph.
        config (dict): Configuration parameters for the graph.
        schema (BaseModel): The schema for the graph output.

    Example:
        >>> smart_scraper = SmartScraperGraph(
        ...     "List me all the attractions in Chioggia.",
        ...     "https://en.wikipedia.org/wiki/Chioggia",
        ...     {"llm": {"model": "gpt-3.5-turbo"}}
        ... )
        >>> result = smart_scraper.run()
        )
    """

    def __init__(self,
                 prompt: str,
                 config: dict,
                 source: Optional[str] = None,
                 schema: Optional[BaseModel] = None):
        self.library = config['library']

        super().__init__(prompt, config, source, schema)

        self.input_key = "url" if source is not None and source.startswith("http") else "local_dir"


    def _create_graph(self) -> BaseGraph:
        """
        Creates the graph of nodes representing the workflow for web scraping.

        Returns:
            BaseGraph: A graph instance representing the web scraping workflow.
        """
        parse_node = ParseNode(
            input="fetched_content",
            output=["parsed_doc"],
            node_config={
                "chunk_size": self.model_token
            }
        )

        generate_answer_node = GenerateAnswerNode(
            input="user_prompt & (relevant_chunks | parsed_doc | doc)",
            output=["answer"],
            node_config={
                "llm_model": self.llm_model,
                "additional_info": self.config.get("additional_info"),
                "schema": self.schema,
            }
        )

        return BaseGraph(
            nodes=[
                parse_node,
                generate_answer_node,
            ],
            edges=[
                (parse_node, generate_answer_node)
            ],
            entry_point=parse_node,
            graph_name=self.__class__.__name__
        )

    def run(self, state: dict) -> str:
        """
        Executes the scraping process and returns the answer to the prompt.

        Returns:
            str: The answer to the prompt.
        """

        inputs = {"user_prompt": self.prompt}
        inputs.update(state)
        self.final_state, self.execution_info = self.graph.execute(inputs)

        return self.final_state.get("answer", "No answer found.")