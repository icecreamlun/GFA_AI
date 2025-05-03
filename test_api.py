import requests
import json

def test_chat():
    url = "http://localhost:8000/chat"
    headers = {"Content-Type": "application/json"}
    data = {
        "query": "Find contractors who have experience with government projects and are located in New Jersey"
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print("Status Code:", response.status_code)
    print("Response:", json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_chat() 