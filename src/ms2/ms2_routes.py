"""API routes for MS2 microservice: clinical trial criteria parser."""


from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic_core._pydantic_core import ValidationError

from src.ms2.ms2_main import MS2Service
from src.ms2.ms2_models import (
    EligibilityCriteria,
    ExampleResponse,
    ParsedCriteriaResponse,
)

router = APIRouter()
service = MS2Service()


class ErrorResponse:
    pass


@router.post(
    "/process",
    response_model=ExampleResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["MS2"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
# async def process_data(request: ExampleRequest) -> ExampleResponse:
#     """
#     Process incoming data.
#
#     Args:
#         request: The request data to process
#
#     Returns:
#         ExampleResponse: Processed result
#
#     Raises:
#         HTTPException: If processing fails
#     """
#     try:
#         result = await service.process(request)
#         return result
#     except ValueError as e:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e),
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Processing failed: {str(e)}",
#         )


@router.get(
    "/items",
    response_model=List[ExampleResponse],
    tags=["MS2"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
# async def get_items() -> List[ExampleResponse]:
#     """
#     Retrieve all items.
#
#     Returns:
#         List[ExampleResponse]: List of all items
#     """
#     try:
#         items = await service.get_all_items()
#         return items
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve items: {str(e)}",
#         )


@router.get(
    "/items/{item_id}",
    response_model=ExampleResponse,
    tags=["MS2"],
    responses={
        404: {"model": ErrorResponse, "description": "Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
# async def get_item(item_id: int) -> ExampleResponse:
#     """
#     Retrieve a specific item by ID.
#
#     Args:
#         item_id: The ID of the item to retrieve
#
#     Returns:
#         ExampleResponse: The requested item
#
#     Raises:
#         HTTPException: If item not found or retrieval fails
#     """
#     try:
#         item = await service.get_item_by_id(item_id)
#         if item is None:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Item with ID {item_id} not found",
#             )
#         return item
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to retrieve item: {str(e)}",
#         )


@router.post(
    "/parse-criteria/{nct_id}",
    response_model=ParsedCriteriaResponse,
    tags=["MS2"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def parse_criteria(nct_id: str, criteria: EligibilityCriteria) -> ParsedCriteriaResponse:
    """
    Parse the eligibility criteria and return a list of rules.

    Args:
        nct_id: The NCT ID of the trial
        criteria: The eligibility criteria to parse

    Returns:
        ParsedCriteriaResponse: The parsed criteria response

    Raises:
        HTTPException: If parsing fails
    """
    try:
        result = await service.parse_criteria(nct_id, criteria.raw_text)
        return result
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Parsing failed: {str(e)}",
        )