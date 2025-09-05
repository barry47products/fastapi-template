# Test Suite Refactoring Roadmap

## Overview

Complete refactoring of test suite from unit/coverage-focused to behaviour-driven testing.

**Principles:**

- Test behaviours, not implementation
- Mock at repository boundaries only
- Each test must run in milliseconds
- No coverage metrics driving decisions
- Test names describe what the system should do

**Progress Tracking:**

- ⬜ Not started
- 🟡 In progress
- ✅ Complete (test passing + all quality checks)

---

## Phase 0: Foundation Setup

### ✅ Archive existing test suite

Move `tests/` to `tmp/archive/tests_backup_2025_08/`

### ✅ Create new test structure

```bash
tests/
├── conftest.py
├── behaviours/
├── contracts/
├── resilience/
└── fixtures/
```

### ✅ Configure pytest without coverage

Update `pyproject.toml` to remove coverage from default runs

### ✅ Update Makefile

- `make test` - runs behaviour tests only (no coverage)
- `make test-cov` - runs with coverage when needed
- `make test-fast` - runs non-slow tests only

---

## Phase 1: System Bootstrap Tests

### ✅ test_should_start_application_successfully

**File:** `tests/contracts/test_health_api.py`
**Verifies:** Application boots with all required components registered

### ✅ test_should_report_healthy_when_all_components_available

**File:** `tests/contracts/test_health_api.py`
**Verifies:** Health endpoint returns healthy status with all checks passing

### ✅ test_should_expose_required_api_endpoints

**File:** `tests/contracts/test_health_api.py`
**Verifies:** All required endpoints are registered and accessible

---

## Phase 2: Message Processing Pipeline

### ✅ test_should_extract_endorsement_from_group_message_with_phone

**File:** `tests/behaviours/test_endorsement_capture.py`
**Verifies:** Provider mention with phone number creates endorsement

### ✅ test_should_extract_endorsement_from_group_message_without_phone

**File:** `tests/behaviours/test_endorsement_capture.py`
**Verifies:** Provider mention without phone still creates endorsement

### ✅ test_should_extract_multiple_endorsements_from_single_message

**File:** `tests/behaviours/test_endorsement_capture.py`
**Verifies:** Multiple provider mentions create multiple endorsements

### ✅ test_should_ignore_individual_whatsapp_messages

**File:** `tests/behaviours/test_endorsement_capture.py`
**Verifies:** Non-group messages (no @g.us) are skipped

### ✅ test_should_handle_empty_message_gracefully

**File:** `tests/behaviours/test_endorsement_capture.py`
**Verifies:** Empty/null message text doesn't crash system

### ✅ test_should_not_create_endorsement_for_non_provider_content

**File:** `tests/behaviours/test_endorsement_capture.py`
**Verifies:** General chat messages don't create false endorsements

---

## Phase 3: Message Classification

### ✅ test_should_classify_recommendation_as_endorsement

**File:** `tests/behaviours/test_message_classification.py`
**Verifies:** "I recommend John the plumber" → RECOMMENDATION type

### ✅ test_should_classify_question_as_query

**File:** `tests/behaviours/test_message_classification.py`
**Verifies:** "Anyone know a good electrician?" → REQUEST type

### ✅ test_should_classify_service_advertisement_as_offer

**File:** `tests/behaviours/test_message_classification.py`
**Verifies:** "I do plumbing, call me" → UNKNOWN type (service offer)

### ✅ test_should_classify_general_chat_as_general

**File:** `tests/behaviours/test_message_classification.py`
**Verifies:** "Beautiful weather today" → UNKNOWN type (general chat)

### ✅ test_should_classify_mixed_content_by_primary_intent

**File:** `tests/behaviours/test_message_classification.py`
**Verifies:** Message with query + endorsement classified by dominant intent

---

## Phase 4: Provider Lifecycle

### ✅ test_should_create_new_provider_on_first_mention

**File:** `tests/behaviours/test_provider_lifecycle.py`
**Verifies:** First mention of provider creates new record

### ✅ test_should_increment_endorsement_count_for_existing_provider

**File:** `tests/behaviours/test_provider_lifecycle.py`
**Verifies:** Subsequent mentions increment count

### ✅ test_should_deduplicate_providers_by_phone_number

**File:** `tests/behaviours/test_provider_lifecycle.py`
**Verifies:** Same phone number = same provider

### ✅ test_should_merge_provider_names_with_same_phone

**File:** `tests/behaviours/test_provider_lifecycle.py`
**Verifies:** "John" and "Johnny" with same phone get merged

### ✅ test_should_update_provider_category_from_mentions

**File:** `tests/behaviours/test_provider_lifecycle.py`
**Verifies:** Provider category refined based on context

---

## Phase 5: Provider Discovery

### ✅ test_should_find_providers_by_exact_category_match

**File:** `tests/behaviours/test_provider_discovery.py`
**Verifies:** Search "plumber" returns all plumbers

### ✅ test_should_find_providers_by_partial_name_match

**File:** `tests/behaviours/test_provider_discovery.py`
**Verifies:** Search "Dav" matches "Davies Electrical"

### ✅ test_should_rank_providers_by_endorsement_count

**File:** `tests/behaviours/test_provider_discovery.py`
**Verifies:** Higher endorsement count = higher ranking

### ✅ test_should_filter_providers_by_location

**File:** `tests/behaviours/test_provider_discovery.py`
**Verifies:** Location-based filtering when available

### ✅ test_should_return_empty_list_for_no_matches

**File:** `tests/behaviours/test_provider_discovery.py`
**Verifies:** No matches returns empty list, not error

---

## Phase 6: Data Extraction

### ✅ test_should_normalize_phone_numbers_to_e164

**File:** `tests/behaviours/test_data_extraction.py`
**Verifies:** "082 123 4567" → "+27821234567"

### ✅ test_should_extract_provider_name_from_patterns

**File:** `tests/behaviours/test_data_extraction.py`
**Verifies:** "John the plumber" → name: "John", service: "plumber"

### ✅ test_should_extract_multiple_phone_numbers

**File:** `tests/behaviours/test_data_extraction.py`
**Verifies:** Message with multiple numbers extracts all

### ✅ test_should_associate_service_keywords_with_names

**File:** `tests/behaviours/test_data_extraction.py`
**Verifies:** "electrician" near "Davies" gets associated

### ✅ test_should_extract_location_references

**File:** `tests/behaviours/test_data_extraction.py`
**Verifies:** "in Constantia" → location: "Constantia"

---

## Phase 7: Webhook API Contract

### ✅ test_should_accept_valid_green_api_webhook

**File:** `tests/contracts/test_webhook_api.py`
**Verifies:** Valid webhook payload returns 200 OK

### ✅ test_should_reject_webhook_without_api_key

**File:** `tests/contracts/test_webhook_api.py`
**Verifies:** Missing API key returns 401

### ✅ test_should_reject_webhook_with_invalid_api_key

**File:** `tests/contracts/test_webhook_api.py`
**Verifies:** Wrong API key returns 401

### ✅ test_should_enforce_rate_limits

**File:** `tests/contracts/test_webhook_api.py`
**Verifies:** Exceeding rate limit returns 429

### ✅ test_should_validate_webhook_signature

**File:** `tests/contracts/test_webhook_api.py`
**Verifies:** Invalid HMAC signature returns 401

### ✅ test_should_return_acknowledgment_for_processed_message

**File:** `tests/contracts/test_webhook_api.py`
**Verifies:** Successful processing returns proper response

---

## Phase 8: Admin API Contract

### ✅ test_should_return_safe_config_without_secrets

**File:** `tests/contracts/test_admin_api.py`
**Verifies:** Config endpoint excludes API keys and secrets

### ✅ test_should_return_service_registry_status

**File:** `tests/contracts/test_admin_api.py`
**Verifies:** Service status shows component health

### ✅ test_should_return_application_info

**File:** `tests/contracts/test_admin_api.py`
**Verifies:** App info includes version and environment

### ✅ test_should_require_authentication_for_admin_endpoints

**File:** `tests/contracts/test_admin_api.py`
**Verifies:** Admin endpoints require valid API key

---

## Phase 9: Error Handling & Resilience

### ✅ test_should_handle_malformed_json_gracefully

**File:** `tests/resilience/test_error_handling.py`
**Verifies:** Bad JSON returns 400, not 500

### ✅ test_should_handle_firestore_timeout_gracefully

**File:** `tests/resilience/test_error_handling.py`
**Verifies:** Database timeout returns appropriate error

### ✅ test_should_rollback_on_partial_failure

**File:** `tests/resilience/test_error_handling.py`
**Verifies:** Failed transaction doesn't leave partial data

### ✅ test_should_validate_phone_numbers_before_processing

**File:** `tests/resilience/test_data_validation.py`
**Verifies:** Invalid phone format returns validation error

### ✅ test_should_validate_group_id_format

**File:** `tests/resilience/test_data_validation.py`
**Verifies:** Invalid group ID format returns validation error

### ✅ test_should_handle_duplicate_endorsements

**File:** `tests/resilience/test_data_validation.py`
**Verifies:** Duplicate endorsements handled appropriately

---

## Phase 10: Security Boundaries

### ✅ test_should_prevent_sql_injection_in_search

**File:** `tests/resilience/test_security_boundaries.py`
**Verifies:** Malicious search input safely handled

### ✅ test_should_sanitise_user_input_in_messages

**File:** `tests/resilience/test_security_boundaries.py`
**Verifies:** Script tags and HTML stripped from input

### ✅ test_should_enforce_request_size_limits

**File:** `tests/resilience/test_security_boundaries.py`
**Verifies:** Oversized requests rejected

### ✅ test_should_mask_sensitive_data_in_logs

**File:** `tests/resilience/test_security_boundaries.py`
**Verifies:** Phone numbers and IDs masked in logs

---

## Completion Criteria

- [x] All tests passing (50 tests in 0.08s)
- [x] All quality checks passing (black, ruff, mypy, isort)
- [x] Old test suite archived (moved to tmp/archive/tests_backup_2025_08/)
- [ ] CI/CD updated to use new tests
- [x] Test execution time < 5 seconds for full suite (0.08s achieved)
- [x] No coverage requirements in default test runs

---

## Notes

**Test Implementation Order:**
Follow phases sequentially. Each phase builds on the previous one.

**Mocking Strategy:**

- Mock at repository boundaries
- Use builders for complex test data
- Share fixtures where sensible

**Performance Target:**

- Individual test: < 50ms
- Full suite: < 5 seconds
- Parallel execution enabled for CI

**Next Test to Implement:**
Always check the first ⬜ item in the list.
