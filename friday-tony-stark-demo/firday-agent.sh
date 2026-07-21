step 1: Create a new file named "firday-agent.sh" and add the following code:
echo "================================================================"
echo "================================================================"
echo "===   ______ ______   _____  _____     _    __      __       ==="
echo "===  |  ____||  __  ||_   _||  __ \   / \   \ \    / /       ==="
echo "===  | |__   | |__| |  | |  | |  \ \ / _ \   \ \__/ /        ==="
echo "===  |  __|  |  _  /   | |  | |  | || |_| |   \    /         ==="
echo "===  | |     | | \ \  _| |_ | |__/ /|  _  |    |  |          ==="
echo "===  |_|     |_|  \_\ |_____||____/ |_| |_|    |__|          ==="
echo "================================================================"
echo "=========================== CONTROL ============================"
echo "================================================================"

echo "Starting Friday Agent..."
echo "Loading modules..."
sleep 2 # Simulate loading time
echo "Modules loaded successfully!"
echo "Initializing systems..."
sleep 3 # Simulate initialization time
echo "Systems initialized successfully!"
echo "Friday Agent is now online and ready to assist you!"
echo "================================================================"
echo "Available Commands:"
echo "1. 'Friday, what's the weather like today?'"
echo "2. 'Friday, set a reminder for my meeting at 3 PM.'"
echo "3. 'Friday, play some music.'"
echo "4. 'Friday, turn on the lights.'"
echo "5. 'Friday, what's on my calendar for tomorrow?'"
echo "6. 'Friday, tell me a joke.'"
echo "7. 'Friday, how's the traffic to work?'"
echo "8. 'Friday, what's the news today?'"
echo "9. 'Friday, find me a nearby restaurant.'"
echo "10. 'Friday, what's the stock price of [company]?'"
echo "================================================================"
echo "Type your command below:"
while true; do
    read -p "> " command
    case "$command" in
        "Friday, what's the weather like today?")
            echo "The weather today is sunny with a high of 75°F and a low of 55°F."
            ;;
        "Friday, set a reminder for my meeting at 3 PM.")
            echo "Reminder set for your meeting at 3 PM."
            ;;
        "Friday, play some music.")
            echo "Playing your favorite playlist."
            ;;
        "Friday, turn on the lights.")
            echo "Turning on the lights."
            ;;
        "Friday, what's on my calendar for tomorrow?")
            echo "You have a meeting with the marketing team at 10 AM and a lunch appointment at 12 PM."
            ;;
        "Friday, tell me a joke.")
            echo "Why don't scientists trust atoms? Because they make up everything!"
            ;;
        "Friday, how's the traffic to work?")
            echo "The traffic to work is currently light, with an estimated travel time of 30 minutes."
            ;;
        "Friday, what's the news today?")
            echo "Today's top news: The stock market is up, and a new tech product has been released."
            ;;
        "Friday, find me a nearby restaurant.")
            echo "Here are some nearby restaurants: 1. The Italian Bistro, 2. The Sushi Place, 3. The Vegan Cafe."
            ;;
        "Friday, what's the stock price of "*)
            company=$(echo "$command" | sed 's/Friday, what's the stock price of //')
            echo "The current stock price of $company is $150.00."
            ;;
        *)
            echo "Sorry, I didn't understand that command. Please try again."
            ;;
    esac
done

step 2: Save the file and make it executable by running the following command in the terminal:
chmod +x firday-agent.sh
step 3: Run the script by executing the following command in the terminal:
./firday-agent.sh
You should see the welcome message and the list of available commands. You can type any of the
commands to see the corresponding response from the Friday Agent.
Note: This is a simple simulation of a virtual assistant and does not have actual functionality. The responses are hardcoded for demonstration purposes.

