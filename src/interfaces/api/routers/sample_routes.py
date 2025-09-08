"""
Sample CRUD API endpoints demonstrating FastAPI patterns.

This module provides example RESTful endpoints showing:
- CRUD operations (Create, Read, Update, Delete)
- Request/response schemas with Pydantic
- Dependency injection patterns
- Error handling and validation
- Security with API key authentication
- Rate limiting

Replace this with your own business logic and entities.
"""

from datetime import datetime, UTC
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.infrastructure.observability import get_logger, get_metrics_collector
from src.infrastructure.security import check_rate_limit, verify_api_key

# Constants for reusable field descriptions and messages
USER_FULL_NAME_DESC = "User's full name"
USER_AGE_DESC = "User's age"
USER_NOT_FOUND_MSG = "User not found"


# Sample request/response schemas
class CreateUserRequest(BaseModel):
    """Request schema for creating a new user."""

    name: str = Field(min_length=2, max_length=100, description=USER_FULL_NAME_DESC)
    email: str = Field(description="User's email address")
    age: int = Field(ge=18, le=120, description=USER_AGE_DESC)


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: str = Field(description="Unique user identifier")
    name: str = Field(description=USER_FULL_NAME_DESC)
    email: str = Field(description="User's email address")
    age: int = Field(description=USER_AGE_DESC)
    created_at: datetime = Field(description="When the user was created")
    updated_at: datetime = Field(description="When the user was last updated")


class UpdateUserRequest(BaseModel):
    """Request schema for updating user data."""

    name: str | None = Field(None, min_length=2, max_length=100, description=USER_FULL_NAME_DESC)
    age: int | None = Field(None, ge=18, le=120, description=USER_AGE_DESC)


class CreateProductRequest(BaseModel):
    """Request schema for creating a new product."""

    name: str = Field(min_length=2, max_length=200, description="Product name")
    description: str = Field(max_length=1000, description="Product description")
    price: float = Field(gt=0, description="Product price")
    category: str = Field(max_length=50, description="Product category")


class ProductResponse(BaseModel):
    """Response schema for product data."""

    id: str = Field(description="Unique product identifier")
    name: str = Field(description="Product name")
    description: str = Field(description="Product description")
    price: float = Field(description="Product price")
    category: str = Field(description="Product category")
    created_at: datetime = Field(description="When the product was created")
    in_stock: bool = Field(description="Whether product is in stock")


# Router with sample endpoints
router = APIRouter(
    prefix="/api/v1",
    tags=["samples"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)

logger = get_logger(__name__)
metrics = get_metrics_collector()

# In-memory storage for demonstration (replace with your database/repository)
_users_storage: dict[str, dict[str, Any]] = {}
_products_storage: dict[str, dict[str, Any]] = {}


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user_request: CreateUserRequest) -> UserResponse:
    """
    Create a new user.

    Demonstrates:
    - POST endpoint with request validation
    - Response model with proper status code
    - Logging and metrics collection
    - Basic business logic

    Replace this with your actual user creation logic.
    """
    logger.info("Creating new user", name=user_request.name, email=user_request.email)

    # Check if user already exists (simple email check)
    for existing_user in _users_storage.values():
        if existing_user["email"] == user_request.email:
            logger.warning("User creation failed - email already exists", email=user_request.email)
            metrics.increment_counter("user_creation_failures_total", {"reason": "email_exists"})
            raise HTTPException(status_code=400, detail="User with this email already exists")

    # Create new user
    user_id = str(uuid4())
    now = datetime.now(UTC)

    user_data = {
        "id": user_id,
        "name": user_request.name,
        "email": user_request.email,
        "age": user_request.age,
        "created_at": now,
        "updated_at": now,
    }

    _users_storage[user_id] = user_data

    logger.info("User created successfully", user_id=user_id, email=user_request.email)
    metrics.increment_counter("users_created_total", {})

    return UserResponse(
        id=user_id,
        name=user_request.name,
        email=user_request.email,
        age=user_request.age,
        created_at=now,
        updated_at=now,
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of users to return"),
    offset: int = Query(default=0, ge=0, description="Number of users to skip"),
) -> list[UserResponse]:
    """
    List users with pagination.

    Demonstrates:
    - GET endpoint with query parameters
    - Pagination using limit/offset
    - List response model
    - Query parameter validation
    """
    logger.info("Listing users", limit=limit, offset=offset)

    all_users = list(_users_storage.values())
    paginated_users = all_users[offset : offset + limit]

    metrics.increment_counter("user_list_requests_total", {})
    metrics.record_histogram(
        "user_list_response_size", len(paginated_users), {"requested_limit": str(limit)}
    )

    return [UserResponse(**user) for user in paginated_users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str) -> UserResponse:
    """
    Get a specific user by ID.

    Demonstrates:
    - GET endpoint with path parameter
    - 404 handling for missing resources
    - Single resource response
    """
    logger.info("Retrieving user", user_id=user_id)

    if user_id not in _users_storage:
        logger.warning("User not found", user_id=user_id)
        metrics.increment_counter("user_not_found_total", {})
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND_MSG)

    user_data = _users_storage[user_id]
    logger.info("User retrieved successfully", user_id=user_id)
    metrics.increment_counter("user_retrieved_total", {})

    return UserResponse(**user_data)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, update_request: UpdateUserRequest) -> UserResponse:
    """
    Update an existing user.

    Demonstrates:
    - PUT endpoint for updates
    - Partial update handling
    - Resource existence validation
    - Update timestamp management
    """
    logger.info("Updating user", user_id=user_id)

    if user_id not in _users_storage:
        logger.warning("User update failed - user not found", user_id=user_id)
        metrics.increment_counter("user_update_failures_total", {"reason": "not_found"})
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND_MSG)

    user_data = _users_storage[user_id].copy()

    # Apply updates only for provided fields
    update_count = 0
    if update_request.name is not None:
        user_data["name"] = update_request.name
        update_count += 1
    if update_request.age is not None:
        user_data["age"] = update_request.age
        update_count += 1

    if update_count > 0:
        user_data["updated_at"] = datetime.now(UTC)
        _users_storage[user_id] = user_data

    logger.info("User updated successfully", user_id=user_id, fields_updated=update_count)
    metrics.increment_counter("users_updated_total", {})

    return UserResponse(**user_data)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str) -> None:
    """
    Delete a user.

    Demonstrates:
    - DELETE endpoint
    - 204 No Content response
    - Resource deletion handling
    """
    logger.info("Deleting user", user_id=user_id)

    if user_id not in _users_storage:
        logger.warning("User deletion failed - user not found", user_id=user_id)
        metrics.increment_counter("user_deletion_failures_total", {"reason": "not_found"})
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND_MSG)

    del _users_storage[user_id]

    logger.info("User deleted successfully", user_id=user_id)
    metrics.increment_counter("users_deleted_total", {})


@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(product_request: CreateProductRequest) -> ProductResponse:
    """
    Create a new product.

    Demonstrates:
    - Multiple entity types in same router
    - Different validation rules per entity
    - Complex business objects
    """
    logger.info(
        "Creating new product", name=product_request.name, category=product_request.category
    )

    product_id = str(uuid4())
    now = datetime.now(UTC)

    product_data = {
        "id": product_id,
        "name": product_request.name,
        "description": product_request.description,
        "price": product_request.price,
        "category": product_request.category,
        "created_at": now,
        "in_stock": True,  # Default to in stock
    }

    _products_storage[product_id] = product_data

    logger.info(
        "Product created successfully", product_id=product_id, category=product_request.category
    )
    metrics.increment_counter("products_created_total", {"category": product_request.category})

    return ProductResponse(
        id=product_id,
        name=product_request.name,
        description=product_request.description,
        price=product_request.price,
        category=product_request.category,
        created_at=now,
        in_stock=True,
    )


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    category: str | None = Query(None, description="Filter by product category"),
    in_stock_only: bool = Query(False, description="Show only products in stock"),
    limit: int = Query(
        default=20, ge=1, le=100, description="Maximum number of products to return"
    ),
) -> list[ProductResponse]:
    """
    List products with filtering.

    Demonstrates:
    - Query parameter filtering
    - Boolean query parameters
    - Optional filtering
    - Complex query logic
    """
    logger.info("Listing products", category=category, in_stock_only=in_stock_only, limit=limit)

    all_products = list(_products_storage.values())

    # Apply filters
    filtered_products = all_products
    if category:
        filtered_products = [p for p in filtered_products if p["category"] == category]
    if in_stock_only:
        filtered_products = [p for p in filtered_products if p["in_stock"]]

    # Apply limit
    limited_products = filtered_products[:limit]

    logger.info(
        "Products filtered",
        total_available=len(all_products),
        after_filtering=len(filtered_products),
        returned=len(limited_products),
    )
    metrics.increment_counter("product_list_requests_total", {"category": category or "all"})

    return [ProductResponse(**product) for product in limited_products]


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str) -> ProductResponse:
    """Get a specific product by ID."""
    logger.info("Retrieving product", product_id=product_id)

    if product_id not in _products_storage:
        logger.warning("Product not found", product_id=product_id)
        metrics.increment_counter("product_not_found_total", {})
        raise HTTPException(status_code=404, detail="Product not found")

    product_data = _products_storage[product_id]
    logger.info("Product retrieved successfully", product_id=product_id)
    metrics.increment_counter("products_retrieved_total", {})

    return ProductResponse(**product_data)


@router.post("/webhook/sample", status_code=200)
async def sample_webhook(payload: dict[str, Any]) -> dict[str, str]:
    """
    Sample webhook endpoint showing webhook patterns.

    Demonstrates:
    - Webhook payload handling
    - Generic payload processing
    - Webhook response patterns

    Replace this with your actual webhook processing logic.
    For production webhooks, consider:
    - HMAC signature verification
    - Idempotency handling
    - Async processing for heavy payloads
    """
    operation_start = datetime.now(UTC)

    logger.info("Received webhook payload", payload_keys=list(payload.keys()) if payload else [])

    # Sample webhook processing
    webhook_type = payload.get("type", "unknown")
    webhook_id = payload.get("id", "unknown")

    # Log payload details (be careful with sensitive data in production)
    logger.info(
        "Processing webhook",
        webhook_type=webhook_type,
        webhook_id=webhook_id,
        payload_size=len(str(payload)),
    )

    # Sample processing duration
    processing_duration = (datetime.now(UTC) - operation_start).total_seconds()

    metrics.increment_counter("webhooks_processed_total", {"type": webhook_type})
    metrics.record_histogram(
        "webhook_processing_duration_seconds", processing_duration, {"type": webhook_type}
    )

    logger.info(
        "Webhook processed successfully",
        webhook_type=webhook_type,
        duration_seconds=processing_duration,
    )

    return {
        "status": "processed",
        "webhook_type": webhook_type,
        "processing_time_ms": str(round(processing_duration * 1000, 2)),
        "message": "Webhook received and processed successfully",
    }
