# External Services Testing

This guide covers testing with external services using Testcontainers and Docker Compose.

## Overview

Integration tests often need real external services:
- Databases (PostgreSQL, MySQL, MongoDB)
- Caches (Redis, Memcached)
- Message queues (RabbitMQ, Kafka)
- Search engines (Elasticsearch)
- Cloud services (S3, SQS)

**Problem:** Running real services locally is complex and inconsistent.

**Solutions:**
1. **Testcontainers** - Programmatic Docker containers for testing
2. **Docker Compose** - Declarative test environment
3. **Mock services** - When real services aren't feasible

---

## Testcontainers (Recommended)

Testcontainers provides lightweight, throwaway instances of services in Docker containers.

### Installation

```bash
uv add -D testcontainers pytest-testcontainers
```

### Benefits

✓ **Real services** - Not mocks, actual database/service behavior
✓ **Isolated** - Each test can have its own container
✓ **Automatic cleanup** - Containers destroyed after tests
✓ **Dynamic ports** - Avoids port conflicts in CI/CD
✓ **Consistent** - Same environment local and CI
✓ **Fast** - Containers start in 1-3 seconds

### Basic Pattern

```python
from testcontainers.postgres import PostgresContainer
import pytest

@pytest.fixture(scope="module")
def postgres_container():
    """Provide PostgreSQL container for integration tests."""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture
def database_url(postgres_container):
    """Get database connection URL."""
    return postgres_container.get_connection_url()

@pytest.mark.integration
def test_database_operations(database_url):
    engine = create_engine(database_url)
    # Use real PostgreSQL database
    ...
```

---

## Common Testcontainers Patterns

### PostgreSQL

```python
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer(
        "postgres:15",
        username="test",
        password="test",
        dbname="testdb"
    ) as postgres:
        yield postgres

@pytest.fixture
def database_session(postgres_container):
    """Provide database session with transaction rollback."""
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)

    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
```

### Redis

```python
from testcontainers.redis import RedisContainer
import redis

@pytest.fixture(scope="module")
def redis_container():
    with RedisContainer("redis:7") as redis_cont:
        yield redis_cont

@pytest.fixture
def redis_client(redis_container):
    """Provide Redis client connected to test container."""
    client = redis.from_url(redis_container.get_connection_url())
    yield client
    client.flushall()  # Clear all data after test
    client.close()

@pytest.mark.integration
def test_cache_operations(redis_client):
    redis_client.set("key", "value")
    assert redis_client.get("key") == b"value"
```

### MongoDB

```python
from testcontainers.mongodb import MongoDbContainer
from pymongo import MongoClient

@pytest.fixture(scope="module")
def mongodb_container():
    with MongoDbContainer("mongo:7") as mongo:
        yield mongo

@pytest.fixture
def mongodb_client(mongodb_container):
    """Provide MongoDB client."""
    client = MongoClient(mongodb_container.get_connection_url())
    yield client
    client.drop_database("testdb")  # Cleanup
    client.close()

@pytest.mark.integration
def test_document_operations(mongodb_client):
    db = mongodb_client.testdb
    collection = db.users

    collection.insert_one({"name": "John", "age": 30})

    user = collection.find_one({"name": "John"})
    assert user["age"] == 30
```

### Kafka

```python
from testcontainers.kafka import KafkaContainer
from kafka import KafkaProducer, KafkaConsumer

@pytest.fixture(scope="module")
def kafka_container():
    with KafkaContainer() as kafka:
        yield kafka

@pytest.fixture
def kafka_producer(kafka_container):
    producer = KafkaProducer(
        bootstrap_servers=kafka_container.get_bootstrap_server()
    )
    yield producer
    producer.close()

@pytest.mark.integration
def test_message_publishing(kafka_producer, kafka_container):
    topic = "test-topic"

    # Produce message
    kafka_producer.send(topic, b"test message")
    kafka_producer.flush()

    # Consume message
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=kafka_container.get_bootstrap_server(),
        auto_offset_reset='earliest'
    )

    messages = []
    for message in consumer:
        messages.append(message.value)
        break

    assert messages[0] == b"test message"
```

### Elasticsearch

```python
from testcontainers.elasticsearch import ElasticSearchContainer
from elasticsearch import Elasticsearch

@pytest.fixture(scope="module")
def elasticsearch_container():
    with ElasticSearchContainer("elasticsearch:8.11.0") as es:
        yield es

@pytest.fixture
def es_client(elasticsearch_container):
    client = Elasticsearch(
        elasticsearch_container.get_url(),
        verify_certs=False
    )
    yield client
    client.close()

@pytest.mark.integration
def test_search_operations(es_client):
    # Index document
    es_client.index(
        index="test-index",
        id=1,
        document={"title": "Test", "content": "Hello World"}
    )
    es_client.indices.refresh(index="test-index")

    # Search
    result = es_client.search(
        index="test-index",
        query={"match": {"content": "Hello"}}
    )

    assert result["hits"]["total"]["value"] == 1
```

---

## Docker Compose for Integration Tests

For complex multi-service environments, use Docker Compose.

### pytest-docker-compose Plugin

```bash
uv add -D pytest-docker-compose
```

### docker-compose.test.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: testdb
    ports:
      - "5432"  # Dynamic port
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7
    ports:
      - "6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  kafka:
    image: confluentinc/cp-kafka:latest
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
    ports:
      - "9092"
    depends_on:
      - zookeeper

  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
```

### pytest Configuration

```python
# tests/integration/conftest.py
import pytest

@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    return pytestconfig.rootdir / "docker-compose.test.yml"

@pytest.fixture(scope="session")
def postgres_service(docker_services):
    """Wait for PostgreSQL to be ready."""
    docker_services.wait_until_responsive(
        timeout=30.0,
        pause=0.5,
        check=lambda: is_postgres_ready(
            docker_services.port_for("postgres", 5432)
        )
    )
    return docker_services.port_for("postgres", 5432)

def is_postgres_ready(port):
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=port,
            user="test",
            password="test",
            dbname="testdb"
        )
        conn.close()
        return True
    except Exception:
        return False

@pytest.fixture
def database_url(postgres_service):
    return f"postgresql://test:test@localhost:{postgres_service}/testdb"
```

### Usage

```python
@pytest.mark.integration
def test_with_postgres(database_url):
    engine = create_engine(database_url)
    # Test with real PostgreSQL
    ...
```

---

## API Testing Patterns

### Testing External APIs

#### Option 1: Mock External API

```python
import responses

@responses.activate
def test_fetch_user_from_api():
    # Mock external API response
    responses.add(
        responses.GET,
        "https://api.example.com/users/123",
        json={"id": 123, "name": "John"},
        status=200
    )

    result = fetch_user_from_external_api(123)

    assert result["name"] == "John"
```

#### Option 2: Test Against Mock Server

```python
from testcontainers.core.container import DockerContainer

@pytest.fixture(scope="module")
def mock_api_server():
    """Run mock API server in container."""
    container = DockerContainer("mockserver/mockserver:latest")
    container.with_exposed_ports(1080)
    container.start()

    # Configure expectations
    setup_mock_expectations(
        f"http://localhost:{container.get_exposed_port(1080)}"
    )

    yield f"http://localhost:{container.get_exposed_port(1080)}"

    container.stop()

@pytest.mark.integration
def test_api_integration(mock_api_server):
    result = call_external_api(base_url=mock_api_server)
    assert result.status_code == 200
```

#### Option 3: Test Against Real Staging API

```python
@pytest.mark.integration
@pytest.mark.slow
def test_real_api_integration():
    """Test against real staging environment."""
    api_url = os.getenv("STAGING_API_URL")
    api_key = os.getenv("STAGING_API_KEY")

    result = call_api(api_url, api_key)

    assert result.status_code == 200
    # Be careful with assertions on staging data
```

---

## FastAPI Integration Testing

### Test Client Pattern

```python
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def api_client(database_session):
    """Provide test client with database override."""
    def get_test_db():
        yield database_session

    app.dependency_overrides[get_db] = get_test_db

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()

@pytest.mark.integration
def test_create_user_endpoint(api_client):
    response = api_client.post("/users", json={
        "username": "testuser",
        "email": "test@example.com"
    })

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
```

### Complete CRUD Test Example

```python
@pytest.mark.integration
class TestUserCRUD:
    """Integration tests for User CRUD operations."""

    def test_create_user(self, api_client, database_session):
        response = api_client.post("/users", json={
            "username": "john",
            "email": "john@example.com"
        })

        assert response.status_code == 201
        user_id = response.json()["id"]

        # Verify in database
        user = database_session.query(User).get(user_id)
        assert user.username == "john"

    def test_get_user(self, api_client, user_factory, database_session):
        # Setup: Create user
        user = user_factory(username="jane")
        database_session.add(user)
        database_session.commit()

        # Test
        response = api_client.get(f"/users/{user.id}")

        assert response.status_code == 200
        assert response.json()["username"] == "jane"

    def test_update_user(self, api_client, user_factory, database_session):
        user = user_factory(username="oldname")
        database_session.add(user)
        database_session.commit()

        response = api_client.put(f"/users/{user.id}", json={
            "username": "newname"
        })

        assert response.status_code == 200

        database_session.refresh(user)
        assert user.username == "newname"

    def test_delete_user(self, api_client, user_factory, database_session):
        user = user_factory()
        database_session.add(user)
        database_session.commit()
        user_id = user.id

        response = api_client.delete(f"/users/{user_id}")

        assert response.status_code == 204

        deleted_user = database_session.query(User).get(user_id)
        assert deleted_user is None
```

---

## Performance Optimization

### Container Reuse (Session Scope)

```python
# Reuse container across all tests in module
@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

# Each test gets fresh session with transaction rollback
@pytest.fixture
def database_session(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    # ... transaction setup
    yield session
    # ... rollback
```

**Result:** Container starts once, tests use transactions for isolation.

### Parallel Execution

```bash
# Run integration tests in parallel
pytest -m integration -n auto
```

**Requirements:**
- Each test must be independent
- Use dynamic ports (Testcontainers does this automatically)
- Avoid shared state

### Selective Test Running

```python
# Mark slow tests
@pytest.mark.integration
@pytest.mark.slow
def test_expensive_operation():
    ...

# Run fast integration tests only
pytest -m "integration and not slow"
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Run integration tests
        run: |
          uv run pytest -m integration -v
```

**Note:** GitHub Actions has Docker pre-installed, so Testcontainers works out of the box.

---

## Best Practices

### ✓ DO

- Use module/session scope for containers (start once)
- Use function scope for database sessions (transaction rollback)
- Wait for services to be ready (health checks)
- Use dynamic ports (avoid conflicts)
- Clean up test data (rollback or delete)
- Tag with `@pytest.mark.integration`
- Run in CI/CD before merging

### ❌ DON'T

- Start containers in every test (too slow)
- Use hardcoded ports (conflicts in CI)
- Share database sessions between tests (not isolated)
- Forget to clean up containers (memory leaks)
- Test every edge case in integration tests (use unit tests)
- Run integration tests on every commit (too slow)

---

## Troubleshooting

### Container Won't Start

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Or check container logs
@pytest.fixture
def postgres_container():
    with PostgresContainer("postgres:15") as postgres:
        print(postgres.get_logs())  # Debug output
        yield postgres
```

### Port Conflicts

Testcontainers uses dynamic ports automatically. If you're manually specifying ports:

```python
# ❌ BAD: Hardcoded port
container.with_bind_ports(5432, 5432)

# ✓ GOOD: Dynamic port
container.with_exposed_ports(5432)
# Get actual port:
port = container.get_exposed_port(5432)
```

### Slow Container Startup

```python
# Use smaller images
PostgresContainer("postgres:15-alpine")  # Smaller, faster

# Or reuse at module/session scope
@pytest.fixture(scope="session")  # Start once for all tests
```

---

## Summary

**Testcontainers:**
- Best for isolated, real service testing
- Automatic cleanup
- Dynamic ports for CI/CD
- Fast startup (1-3 seconds)

**Docker Compose:**
- Best for complex multi-service environments
- Declarative configuration
- Good for local development parity

**When to use what:**
- **Single service:** Testcontainers
- **Multiple services:** Docker Compose or Testcontainers
- **External API:** Mock with `responses` or mock server container
- **Slow/expensive service:** Mock instead of real container
