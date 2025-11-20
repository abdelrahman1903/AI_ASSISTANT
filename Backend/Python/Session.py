from Model import Model
from datetime import datetime, timedelta


class Session:

    sessions = []

    @staticmethod
    def user_chatBot_instance(Token,location = { "latitude": 29.9866, "longitude": 31.4406 }):
        # Find if user already exists
        # Token = Token.strip().replace("Bearer ", "")
        user_session = next((u for u in Session.sessions if u["Token"] == Token), None)
        if user_session is None :
            print("creating new instance")
            new_instance = {"Token": Token, "instance": Model(), "last_active": datetime.now()}
            Session.sessions.append(new_instance)

            # ⚠️⚠️ Initialize user history from DB could be done here insted of in Model class
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            status = new_instance["instance"].init_user_history(location,current_datetime,Token)
            # print(sessions[0])
            return new_instance["instance"]
        else:
            # Update last_active timestamp
            user_session["last_active"] = datetime.now()
            return user_session["instance"]


    # ⚠️⚠️ could be modified for better time complexity by remvoing the final loop 
    @staticmethod
    def remove_idle_sessions():
        print("in")
        now = datetime.now()
        timeout_minutes=1
        to_remove = []
        for s in Session.sessions: 
            if now - s["last_active"] > timedelta(minutes=timeout_minutes): #seconds
                chatBot_instance = s["instance"]
                Bearer_TOKEN = s["Token"]
                # token = authorization.split(" ")[1]  # If format is "Bearer <token>"

                # ⚠️⚠️to be done save history before removal
                status = chatBot_instance.save_history(Bearer_TOKEN)
                print(status)
                if status==200:
                    to_remove.append(s)
        for s in to_remove:
            Session.sessions.remove(s)
        print(len(Session.sessions))
        
