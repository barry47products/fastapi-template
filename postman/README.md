# Neighbour Approved API - Postman Collection

Comprehensive Postman collection for testing the Neighbour Approved WhatsApp-based service endorsement API.

## 📁 Files Included

- **`Neighbour-Approved-Collection.postman_collection.json`** - Complete API collection with tests
- **`Development.postman_environment.json`** - Local development environment variables
- **`Production.postman_environment.json`** - Production environment template
- **`README.md`** - This setup guide

## 🚀 Quick Setup

### 1. Import into Postman

1. Open Postman Desktop or Web App
2. Click **Import** → **Upload Files**
3. Select both collection and environment files:
   - `Neighbour-Approved-Collection.postman_collection.json`
   - `Development.postman_environment.json`
4. Click **Import**

### 2. Select Environment

1. In Postman, click the environment dropdown (top-right)
2. Select **"Neighbour Approved - Development"**
3. Verify the `base_url` shows `http://localhost:8000`

### 3. Start Your Local Server

```bash
# In your project directory
make run
# OR manually:
ENV_FILE=.env.local poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 📋 Collection Structure

### 🏥 Health Endpoints

- **Basic Health Check** - Simple health status (no auth)
- **Detailed Health Check** - Component-level health details
- **Basic Status Check** - System status overview

### 🔧 Admin Endpoints (Requires API Key)

- **Get Application Info** - App version, environment details
- **Get Safe Configuration** - Non-sensitive config display
- **Get Service Status** - Infrastructure component status

### 📱 WhatsApp Webhooks (Requires API Key)

- **Process WhatsApp Group Message** - Main endorsement processing
- **Process Individual Message** - Individual chat handling
- **Service Request Message** - Request classification testing
- **Various Webhook Types** - Status, notification handlers

### 📊 Metrics & Monitoring

- **Prometheus Metrics** - Application metrics endpoint

## 🔑 Environment Variables

### Development Environment

- `base_url`: `http://localhost:8000`
- `api_key`: `dev-api-key-123456789` (from your `.env.local`)
- `whatsapp_group_id`: `12345678901234567890@g.us` (test group ID)
- `whatsapp_sender_id`: `27821234567@c.us` (test sender)
- `test_phone_number`: `082-123-4567` (South African test number)

### Production Environment

- Update `base_url` to your production domain
- Set real `api_key` (keep it secret!)
- Configure real WhatsApp IDs for testing

## 🧪 Testing Features

### Automated Test Scripts

Each request includes automated tests that verify:

- Response status codes (200, 401, 422, etc.)
- Response structure and required fields
- Business logic validation
- Performance thresholds
- Security controls

### Example Tests

```javascript
pm.test("Response status code is 200", function () {
  pm.expect(pm.response.code).to.equal(200);
});

pm.test("Group message processed appropriately", function () {
  const responseJson = pm.response.json();
  pm.expect(responseJson.status).to.equal("processed");
  pm.expect(responseJson.action).to.include("group");
});
```

### Running All Tests

1. Select the collection
2. Click **Run Collection**
3. Choose environment and click **Run Neighbour Approved API**
4. View detailed test results

## 🔒 Security Testing

The collection includes security-focused requests:

- **API Key Authentication** - Tests auth requirements
- **Rate Limiting** - Validates rate limit enforcement
- **Input Validation** - Tests malformed request handling
- **Sensitive Data** - Verifies no secrets in responses

## 📱 WhatsApp Message Examples

### Endorsement Message

```json
{
  "typeWebhook": "incomingMessageReceived",
  "chatId": "12345678901234567890@g.us",
  "senderId": "27821234567@c.us",
  "senderName": "Alice Johnson",
  "textMessage": "I highly recommend John the plumber 082-123-4567! Fixed my kitchen sink perfectly.",
  "timestamp": 1735470000
}
```

### Service Request

```json
{
  "textMessage": "Anyone know a good electrician in Johannesburg? Need rewiring work done urgently."
}
```

## 🛠️ Customization

### Adding New Requests

1. Right-click collection → **Add Request**
2. Set method, URL using `{{base_url}}`
3. Add authentication if needed
4. Include test scripts for validation

### Environment Management

- Create new environments for staging, testing
- Use Postman's variable scopes (global, environment, collection)
- Keep sensitive values as "secret" type

## 🚨 Important Notes

### Security

- **Never commit production API keys** to version control
- Use environment variables for sensitive data
- Regularly rotate API keys

### Development

- Ensure Firestore emulator is running (`localhost:8080`)
- Check application logs for detailed error information
- Use health endpoints to verify system status

### Performance

- Monitor response times in test results
- Health checks should respond under 2 seconds
- WhatsApp processing should complete under 10 seconds

## 🔄 Continuous Integration

This collection can be integrated with Newman for CI/CD:

```bash
# Install Newman
npm install -g newman

# Run collection
newman run Neighbour-Approved-Collection.postman_collection.json \
  -e Development.postman_environment.json \
  --reporters cli,json \
  --reporter-json-export results.json
```

## 📞 Support

For issues with the API or collection:

1. Check application logs
2. Verify environment configuration
3. Test health endpoints first
4. Review Postman console for request details

Happy testing! 🎉
