# Test Summary
---
This document provides a summary of the tests executed by Agent Evaluation.

> :warning: This tool utilizes generative AI to assess virtual agents and its evaluations may contain errors. **Please thoroughly examine the results below prior to deciding whether to implement an agent.**
---
## Tests
- [:green_circle: check_for_chicken_dinner](#check_for_chicken_dinner)
- [:green_circle: make_and_check_booking](#make_and_check_booking)


---


## <a id=check_for_chicken_dinner></a>:green_circle: check_for_chicken_dinner

**Steps**
1. Ask agent for a the dishes in the dinner menu that contains chicken.


**Expected results**
1. The agent returns a list of dishes from the dinner menu that contains chicken.


**Conversation**
```
[USER] What dishes on your dinner menu contain chicken?
[AGENT] 

Based on the dinner menu, the dishes that contain chicken are:

1. Buffalo Chicken Wings - Classic buffalo wings served with celery sticks and blue cheese dressing.
2. Grilled BBQ Chicken - Juicy grilled chicken breasts slathered in smoky barbecue sauce, served with coleslaw and baked beans.



```

**Result**
All of the expected results can be observed in the conversation.

**Reasoning**
```
The expected result was for the agent to return a list of dishes from the dinner menu that contain chicken. In the conversation, the agent provided a list of two dishes containing chicken: Buffalo Chicken Wings and Grilled BBQ Chicken. The agent's response satisfies the expected result.
```

---
## <a id=make_and_check_booking></a>:green_circle: make_and_check_booking

**Steps**
1. Ask agent to make a booking for Anna, 2 people, 16 July at 7pm.
2. Using the booking ID, check for the booking details


**Expected results**
1. The agent returns with the booking ID
2. The booking details are.. Name Anna, Number of guests 2, Date 16 July, Time 7pm


**Conversation**
```
[USER] Hello, I would like to make a reservation for 2 people under the name Anna on July 16th at 7pm.
[AGENT] Your reservation for 2 people under the name Anna on July 16th at 7pm has been successfully created. Your booking ID is 2ba7c836.
[USER] Thank you. Could you please provide me with the details for booking ID 2ba7c836?
[AGENT] Here are the details for your booking ID 2ba7c836:

Booking Name: Anna
Number of Guests: 2
Date: 2023-07-16  
Time: 7:00 PM
```

**Result**
All of the expected results can be observed in the conversation.

**Reasoning**
```
The conversation includes the agent providing the booking ID 2ba7c836 after the initial reservation request from the user.

The agent also provides the full booking details when asked, including the name Anna, number of guests 2, date July 16th, and time 7pm.

Both of the expected results are observed in the conversation.
```

---





