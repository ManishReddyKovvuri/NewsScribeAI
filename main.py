from typing import Annotated

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
import os
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
load_dotenv()
import openai
from io import BytesIO
from langchain.tools import tool
import requests


news_tool = TavilySearchResults(max_results=2)

tools = [news_tool]


from langchain_core.messages import SystemMessage

SYSTEM_PROMPT = (
    "You are an AI assistant tasked with helping users create engaging and shareable social media posts. "
    "Leverage the available tools to gather relevant and accurate news or information based on the user's request. "
    "Ensure the generated post is concise, creative, and tailored to the user's needs, while maintaining a friendly and professional tone."
    "Use Emojis and Hashtags to make the post more engaging."
    "generate atleast 500 words of post related content."
    "dont generate the post directly, instead ask the user if they want to generate the post or not."
    "You can only call one tool per turn. If the user asks for multiple things, choose the most relevant or ask them to narrow it down."
)



llm = ChatGroq(model="llama-3.1-8b-instant")


class State(TypedDict):
    messages: Annotated[list, add_messages]


llm_with_tools = llm.bind_tools(tools)



config = {
    "configurable": {
        "thread_id": "1",
        "system_message": SYSTEM_PROMPT
    }
}

def chatbot(state: State):
    system_msg = config["configurable"].get("system_message", "")
    full_messages = [SystemMessage(content=system_msg), *state["messages"]]
    return {"messages": [llm_with_tools.invoke(full_messages)]}



def generate_and_save_image(prompt, image_path):
    """Generates an image using the OpenAI API and saves it to the specified path."""
    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            response_format="url"
        )
        image_url = response.data[0].url

        # Download and save the image
        image_data = requests.get(image_url).content
        img = Image.open(BytesIO(image_data))
        img.save(image_path)

        print(f"Image saved successfully at {image_path}")
    except Exception as e:
        print(f"Error generating or saving image: {e}")




@tool
def ImageGenerator(prompt: str) -> str:
    """Generates an image from a text prompt using DALL·E or another model."""
    # Call OpenAI or Replicate here
    return f"https://fake.url/image-for-{prompt.replace(' ', '-')}.png"






graph_builder = StateGraph(State)

graph_builder.add_node("chatbot", chatbot)

graph_builder.add_node("ImageGenerator", generate_and_save_image)



tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)



graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")
# graph_builder.add_conditional_edges("chatbot", "ImageGenerator")
graph_builder.add_edge("ImageGenerator", END)
graph_builder.add_edge(START, "chatbot")


memory = MemorySaver()

# graph = graph_builder.compile()
graph = graph_builder.compile(checkpointer=memory)

from IPython.display import Image, display

try:
    display(Image(graph.get_graph().draw_mermaid_png()))
    with open("graph_image.png", "wb") as file:
        file.write(graph.get_graph().draw_mermaid_png())

except Exception:
    # This requires some extra dependencies and is optional
    pass

# config = {"configurable": {"thread_id": "1"}}






def stream_graph_updates(user_input: str, config: dict = {}):
    events = graph.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        config,
        stream_mode="values",
    )
    for event in events:
        # each event is a dict like {"messages": [message_dicts]}
        for message in event.get("messages", []):
            if hasattr(message, "pretty_print"):
                message.pretty_print()
                
            else:
                print("Assistant:", message.get("content", "[No content]"))



while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        # if user_input.lower().startswith("/setprompt"):
        #     new_prompt = user_input[len("/setprompt"):].strip()
        #     config["configurable"]["system_message"] = new_prompt
        #     print("✅ System prompt updated.")
        #     continue
        stream_graph_updates(user_input, config=config)
    except Exception as e:
        print("⚠️ Error:", str(e))
        break
