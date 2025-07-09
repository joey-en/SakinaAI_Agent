from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv(".env")

client = OpenAI(
    base_url="https://api.fanar.qa/v1",
    api_key=os.getenv("FANAR_API_KEY"),
)

model_name = "Fanar"
messages = [
    {"role": "user", "content": "hello there who are you?"}

#### NOTES FOR JOY ########
# roles: 
## system	(defines personality and purpose of bot)
## user	what the user said
## assistant	how the bot replied
]

response = client.chat.completions.create(
    model=model_name,
    messages=messages,
)

print("Assistant Response:\n")
print(response.choices[0].message.content)
