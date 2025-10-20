"""Business logic for MS2 microservice."""

from typing import List

from src.ms2.ms2_models import ExampleRequest, ExampleResponse


class MS2Service:
    """Service class containing business logic for MS2."""

    def __init__(self) -> None:
        """Initialize the service."""
        self.items: List[ExampleResponse] = []
        self.next_id: int = 1

    async def process(self, request: ExampleRequest) -> ExampleResponse:
        """
        Process the incoming request.

        Args:
            request: The request data to process

        Returns:
            ExampleResponse: The processed result

        Raises:
            ValueError: If request validation fails
        """
        if not request:
            raise ValueError("Value must be non-negative")

        response = ExampleResponse()

        self.items.append(response)
        self.next_id += 1

        return response

    async def get_all_items(self) -> List[ExampleResponse]:
        """
        Retrieve all items.

        Returns:
            List[ExampleResponse]: List of all processed items
        """
        return self.items

    # async def get_item_by_id(self, item_id: int) -> Optional[ExampleResponse]:
    #     """
    #     Retrieve a specific item by ID.
    #
    #     Args:
    #         item_id: The ID of the item to retrieve
    #
    #     Returns:
    #         Optional[ExampleResponse]: The item if found, None otherwise
    #     """
    #     for item in self.items:
    #         if item.id == item_id:
    #             return item
    #     return None
