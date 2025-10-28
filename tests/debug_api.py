import requests

response = requests.post("http://localhost:8888/api/run_now", json={
    "handler_id": "test-handler-001",
    "method": "write_file",
    "params": {
        "filename": "test.txt",
        "content": "test"
    }
})

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
