from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class NodeStatus(Enum):
    SUCCESS = "✓"
    FAILURE = "⨯"
    NONE = " "


@dataclass
class ValidationNode:
    """Represents a node in the validation tree"""

    name: str
    status: NodeStatus = NodeStatus.NONE
    sample: Optional[str] = None
    error: Optional[str] = None
    count: Optional[int] = None
    children: List["ValidationNode"] = None
    url: Optional[str] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []

    def add_child(self, child: "ValidationNode") -> "ValidationNode":
        self.children.append(child)
        return child


class ValidationTreeBuilder:
    """Builds a validation tree from validation results"""

    def build_tree(
        self,
        source_name: str,
        index_results: Dict[str, Any],
        resource_results: Dict[str, Any],
    ) -> ValidationNode:
        """Build the complete validation tree"""
        root = ValidationNode(name=f"{source_name} Configuration Validation")

        # Add index page subtree
        index_node = self._build_page_subtree(
            "Index Page", index_results, index_results.get("start_url", "")
        )
        root.add_child(index_node)

        # Add resource page subtree
        resource_node = self._build_page_subtree(
            "Resource Page", resource_results, resource_results.get("start_url", "")
        )
        root.add_child(resource_node)

        return root

    def _build_page_subtree(
        self, page_type: str, results: Dict[str, Any], url: str
    ) -> ValidationNode:
        """Build subtree for a page type (index or resource)"""
        has_error = bool(results.get("errors"))
        page_node = ValidationNode(
            name=page_type,
            status=NodeStatus.FAILURE if has_error else NodeStatus.SUCCESS,
            url=url,
        )

        # Add items selector subtree
        items_node = self._build_items_subtree(results.get("items", {}))
        page_node.add_child(items_node)

        # Add pagination subtree
        pagination_node = self._build_pagination_subtree(results.get("pagination", {}))
        page_node.add_child(pagination_node)

        return page_node

    def _build_items_subtree(self, items_data: Dict[str, Any]) -> ValidationNode:
        """Build subtree for items selector and its fields"""
        items_count = items_data.get("count", 0)
        has_error = bool(items_data.get("errors"))

        items_node = ValidationNode(
            name="Items Selector",
            status=NodeStatus.FAILURE if has_error else NodeStatus.SUCCESS,
            sample=f"({items_data.get('selector', '???')})",
            count=items_count,
        )

        # Add field nodes
        fields = ["title", "author", "date", "content", "url"]
        for field in fields:
            field_data = items_data.get("fields", {}).get(field, {})
            if field_data:
                field_node = ValidationNode(
                    name=field.capitalize(),
                    status=NodeStatus.FAILURE
                    if field_data.get("error")
                    else NodeStatus.SUCCESS,
                    sample=field_data.get("sample"),
                    error=field_data.get("error"),
                )
                items_node.add_child(field_node)

        return items_node

    def _build_pagination_subtree(
        self, pagination_data: Dict[str, Any]
    ) -> ValidationNode:
        """Build subtree for pagination information"""
        has_error = bool(pagination_data.get("error"))

        pagination_node = ValidationNode(
            name="Pagination",
            status=NodeStatus.FAILURE if has_error else NodeStatus.SUCCESS,
            sample=f"({pagination_data.get('selector', '???')})",
        )

        # Add chain status
        if has_error:
            pagination_node.add_child(
                ValidationNode(name="Error", error=pagination_data.get("error"))
            )
        else:
            # Add main chain info
            pages_validated = pagination_data.get("pages_validated", 0)
            chain_info = f"Chain: {pages_validated} pages validated"
            chain_node = ValidationNode(name=chain_info)
            pagination_node.add_child(chain_node)

            # Add URLs if available
            urls = pagination_data.get("urls", [])
            if urls:
                for i, url in enumerate(urls, 1):
                    url_node = ValidationNode(name=f"Page {i}", url=url)
                    chain_node.add_child(url_node)

        return pagination_node


class ValidationTreeRenderer:
    """Renders a validation tree as a string"""

    def render(
        self, node: ValidationNode, prefix: str = "", is_last: bool = True
    ) -> str:
        """Render the validation tree as a string"""
        lines = []

        # Prepare the current line
        connector = "└── " if is_last else "├── "
        status_symbol = (
            f" ({node.status.value})" if node.status != NodeStatus.NONE else ""
        )

        # Build the node text
        node_text = node.name + status_symbol
        if node.sample:
            node_text += f" {node.sample}"
        if node.count is not None:
            node_text += f" [{node.count} items found]"
        if node.error:
            node_text += f": {node.error}"
        if node.url:  # Always add URL if present
            node_text += f"\n{prefix}     URL: {node.url}"

        lines.append(prefix + connector + node_text)

        # Prepare the prefix for children
        child_prefix = prefix + ("    " if is_last else "│   ")

        # Render children
        if node.children:
            for i, child in enumerate(node.children):
                is_last_child = i == len(node.children) - 1
                lines.append(self.render(child, child_prefix, is_last_child))

        return "\n".join(lines)


def create_validation_report(
    source_name: str, index_results: Dict[str, Any], resource_results: Dict[str, Any]
) -> str:
    """Create a formatted validation report"""
    builder = ValidationTreeBuilder()
    renderer = ValidationTreeRenderer()

    # Build and render the tree
    tree = builder.build_tree(source_name, index_results, resource_results)
    return renderer.render(tree)
