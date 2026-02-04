import subprocess
import pyttsx3

engine = pyttsx3.init()

print("Type your message (type 'exit' to quit):")

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break

    result = subprocess.run(
        ["ollama", "run", "phi", user_input],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )

    ai_reply = result.stdout.strip()
    print("AI:", ai_reply)

    engine.say(ai_reply)
    engine.runAndWait()
