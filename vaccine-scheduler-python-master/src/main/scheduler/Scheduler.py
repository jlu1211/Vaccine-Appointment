from model.Vaccine import Vaccine
from model.Caregiver import Caregiver
from model.Patient import Patient
from util.Util import Util
import hashlib
import os
from db.ConnectionManager import ConnectionManager
import pymssql
import datetime


'''
objects to keep track of the currently logged-in user
Note: it is always true that at most one of currentCaregiver and currentPatient is not null
        since only one user can be logged-in at a time
'''
current_patient = None

current_caregiver = None


def password_checker(password):
    if len(password) < 8:
        print("Please enter at least 8 characters")
        return False

    has_lowercase = False
    has_uppercase = False
    has_digit = False
    has_special = False

    special_chars = ["!", "@", "#", "?"]

    for char in password:
        if char.islower():
            has_lowercase = True
        if char.isupper():
            has_uppercase = True
        if char.isdigit():
            has_digit = True
        if char in special_chars:
            has_special = True

    if not (has_lowercase and has_uppercase):
        print("Please contain both uppercase and lowercase letters.")
        return False
    if not (has_lowercase and has_digit):
        print("Please contain both letters and numbers.")
        return False
    if not has_special:
        print("Please include at least one special character from \"!\", \"@\", \"#\", \"?\"")
        return False
    return True

def create_patient(tokens):
    username = tokens[1]
    password = tokens[2]

    if not password_checker(password):
        return
    
    if len(tokens) != 3:
        print("Failed to create user.")
        return

    if username_exists_patient(username):
        print("Username taken, try again!")
        return

    salt = os.urandom(16)
    hash = hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000,
            dklen=16)


    patient = Patient(username, salt=salt, hash=hash)

    try:
        patient.save_to_db()
    except pymssql.Error as e:
        print("Failed to create user.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Failed to create user.")
        print(e)
        return
    print("Created user ", username)


def create_caregiver(tokens):
    # create_caregiver <username> <password>
    # check 1: the length for tokens need to be exactly 3 to include all information (with the operation name)
    username = tokens[1]
    password = tokens[2]
    
    if not password_checker(password):
        return
    
    if len(tokens) != 3:
        print("Failed to create user.")
        return

    # check 2: check if the username has been taken already
    if username_exists_caregiver(username):
        print("Username taken, try again!")
        return

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    # create the caregiver
    caregiver = Caregiver(username, salt=salt, hash=hash)

    # save to caregiver information to our database
    try:
        caregiver.save_to_db()
    except pymssql.Error as e:
        print("Failed to create user.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Failed to create user.")
        print(e)
        return
    print("Created user ", username)


def username_exists_caregiver(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Caregivers WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking username")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking username")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False

def username_exists_patient(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Caregivers WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking username")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking username")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False


def login_patient(tokens):
    global current_patient
    if current_caregiver is not None or current_patient is not None:
        print("User already logged in.")
        return

    if len(tokens) != 3:
        print("Login failed.")
        return

    username = tokens[1]
    password = tokens[2]

    patient = None
    try:
        patient = Patient(username, password=password).get()
    except pymssql.Error as e:
        print("Login failed.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Login failed.")
        print("Error:", e)
        return

    # check if the login was successful
    if patient is None:
        print("Login failed.")
    else:
        print("Logged in as: " + username)
        current_patient = patient


def login_caregiver(tokens):
    global current_caregiver
    if current_caregiver is not None or current_patient is not None:
        print("User already logged in.")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Login failed.")
        return

    username = tokens[1]
    password = tokens[2]

    caregiver = None
    try:
        caregiver = Caregiver(username, password=password).get()
    except pymssql.Error as e:
        print("Login failed.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Login failed.")
        print("Error:", e)
        return

    # check if the login was successful
    if caregiver is None:
        print("Login failed.")
    else:
        print("Logged in as: " + username)
        current_caregiver = caregiver


def search_caregiver_schedule(tokens):
    global current_patient
    global current_caregiver

    if current_caregiver is None and current_patient is None:
        print("Please login first!")
        return
    
    if len(tokens) != 2:
        print("Please try again!")
        return
    
    date = tokens[1]
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])

    cm = ConnectionManager()
    conn = cm.create_connection()
    selection = """
        SELECT a.Username, v.Name, v.Doses
        FROM Availabilities a
        LEFT JOIN Vaccines v ON v.Name IS NOT NULL
        WHERE a.Time = %s
        ORDER BY a.Username
        """
    try:
        d = datetime.datetime(year, month, day)
        cursor = conn.cursor(as_dict=True)
        cursor.execute(selection, d)
        for row in cursor:
            print(f"{row['Username']} {row['Name']} {row['Doses']}")
    except pymssql.Error as e:
        print("Error occurred when checking date")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking date")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False


def reserve(tokens):
    global current_patient
    global current_caregiver

    if current_patient is None and current_caregiver is None:
        print("Please login first!")
        return
    
    if current_caregiver is not None:
        print("Please login as a patient!")
        return

    if len(tokens) != 3:
        print("Please try again!")
        return

    date = tokens[1]
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])
    d = datetime.datetime(year, month, day)
    vaccine_name = tokens[2]

    cm = ConnectionManager()
    conn = cm.create_connection()

    try:
        cursor = conn.cursor()
        app_id_query = "SELECT MAX(app_id) FROM Appointments"
        cursor.execute(app_id_query)
        result = cursor.fetchone()
        if result[0] is None:
            app_id = 1
        else:
            app_id = result[0] + 1

        vaccine_query = "SELECT Doses FROM Vaccines WHERE Name = %s"
        cursor.execute(vaccine_query, vaccine_name)
        vaccine_doses = cursor.fetchone()
        if not vaccine_doses or vaccine_doses[0] < 1:
            print("Not enough available doses!")
            return

        caregiver_query = """
            SELECT Username 
            FROM Availabilities 
            WHERE Time = %s
            ORDER BY Username
        """
        cursor.execute(caregiver_query, d)
        caregiver_result = cursor.fetchone()
        if not caregiver_result:
            print("No Caregiver is available!")
            return

        caregiver_username = caregiver_result[0]

        appointment_insert_query = """
            INSERT INTO Appointments (app_id, p_username, c_username, v_name, Time) 
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(appointment_insert_query, (app_id, current_patient.username, caregiver_username, vaccine_name, d))
        conn.commit()

        delete_avail_query = "DELETE FROM Availabilities WHERE Username = %s AND Time = %s"
        cursor.execute(delete_avail_query, (caregiver_username, d))
        conn.commit()

        print(f"Appointment ID: {app_id}, Caregiver username: {caregiver_username}")

        update_vaccine_query = "UPDATE Vaccines SET Doses = Doses - 1 WHERE Name = %s"
        cursor.execute(update_vaccine_query, vaccine_name)
        conn.commit()

    except pymssql.Error as e:
        print("Error occurred when making reservation")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when making reservation")
        print("Error:", e)
    finally:
        cm.close_connection()


def upload_availability(tokens):
    #  upload_availability <date>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    # check 2: the length for tokens need to be exactly 2 to include all information (with the operation name)
    if len(tokens) != 2:
        print("Please try again!")
        return

    date = tokens[1]
    # assume input is hyphenated in the format mm-dd-yyyy
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])
    try:
        d = datetime.datetime(year, month, day)
        current_caregiver.upload_availability(d)
    except pymssql.Error as e:
        print("Upload Availability Failed")
        print("Db-Error:", e)
        quit()
    except ValueError:
        print("Please enter a valid date!")
        return
    except Exception as e:
        print("Error occurred when uploading availability")
        print("Error:", e)
        return
    print("Availability uploaded!")


def cancel(tokens):
    pass


def add_doses(tokens):
    #  add_doses <vaccine> <number>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    #  check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    vaccine_name = tokens[1]
    doses = int(tokens[2])
    vaccine = None
    try:
        vaccine = Vaccine(vaccine_name, doses).get()
    except pymssql.Error as e:
        print("Error occurred when adding doses")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when adding doses")
        print("Error:", e)
        return

    # if the vaccine is not found in the database, add a new (vaccine, doses) entry.
    # else, update the existing entry by adding the new doses
    if vaccine is None:
        vaccine = Vaccine(vaccine_name, doses)
        try:
            vaccine.save_to_db()
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    else:
        # if the vaccine is not null, meaning that the vaccine already exists in our table
        try:
            vaccine.increase_available_doses(doses)
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    print("Doses updated!")



def show_appointments(tokens):
    global current_patient
    global current_caregiver

    if len(tokens) != 1:
        print("Please try again!")
        return

    if current_patient is None and current_caregiver is None:
        print("Please login first!")
        return

    cm = ConnectionManager()
    conn = cm.create_connection()

    try:
        cursor = conn.cursor(as_dict=True)
        if current_patient is not None:
            query = """
                SELECT app_id, v_name, Time, c_username 
                FROM Appointments 
                WHERE p_username = %s 
                ORDER BY app_id
            """
            cursor.execute(query, current_patient.username)
        elif current_caregiver is not None:
            query = """
                SELECT app_id, v_name, Time, p_username 
                FROM Appointments 
                WHERE c_username = %s 
                ORDER BY app_id
            """
            cursor.execute(query, current_caregiver.username)

        appointments = cursor.fetchall()
        if not appointments:
            print("No scheduled appointments.")
            return

        for row in appointments:
            appointment_id = row['app_id']
            vaccine_name = row['v_name']
            appointment_date = row['Time']
            username = row['p_username'] if current_caregiver is not None else row['c_username']
            print(f"{appointment_id} {vaccine_name} {appointment_date} {username}")

    except pymssql.Error as e:
        print("Please try again!")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Please try again!")
        print("Error:", e)
    finally:
        cm.close_connection()




def logout(tokens):
    global current_caregiver
    global current_patient

    if len(tokens) != 1:
        print("Please try again!")
        return

    if current_caregiver is None and current_patient is None:
        print("Please login first.")
        return
    if current_caregiver is not None:
        print("Successfully logged out!")
        current_caregiver = None
        return
    elif current_patient is not None:
        print("Successfully logged out!")
        current_patient = None
        return
    else:
        print("Please try again!")
        return



def start():
    stop = False
    print()
    print(" *** Please enter one of the following commands *** ")
    print("> create_patient <username> <password>")  # //TODO: implement create_patient (Part 1)
    print("> create_caregiver <username> <password>")
    print("> login_patient <username> <password>")  # // TODO: implement login_patient (Part 1)
    print("> login_caregiver <username> <password>")
    print("> search_caregiver_schedule <date>")  # // TODO: implement search_caregiver_schedule (Part 2)
    print("> reserve <date> <vaccine>")  # // TODO: implement reserve (Part 2)
    print("> upload_availability <date>")
    print("> cancel <appointment_id>")  # // TODO: implement cancel (extra credit)
    print("> add_doses <vaccine> <number>")
    print("> show_appointments")  # // TODO: implement show_appointments (Part 2)
    print("> logout")  # // TODO: implement logout (Part 2)
    print("> Quit")
    print()
    while not stop:
        response = ""
        print("> ", end='')

        try:
            response = str(input())
        except ValueError:
            print("Please try again!")
            break

        # response = response.lower()
        tokens = response.split(" ")
        if len(tokens) == 0:
            ValueError("Please try again!")
            continue
        operation = tokens[0]
        if operation == "create_patient":
            create_patient(tokens)
        elif operation == "create_caregiver":
            create_caregiver(tokens)
        elif operation == "login_patient":
            login_patient(tokens)
        elif operation == "login_caregiver":
            login_caregiver(tokens)
        elif operation == "search_caregiver_schedule":
            search_caregiver_schedule(tokens)
        elif operation == "reserve":
            reserve(tokens)
        elif operation == "upload_availability":
            upload_availability(tokens)
        elif operation == cancel:
            cancel(tokens)
        elif operation == "add_doses":
            add_doses(tokens)
        elif operation == "show_appointments":
            show_appointments(tokens)
        elif operation == "logout":
            logout(tokens)
        elif operation == "quit":
            print("Bye!")
            stop = True
        else:
            print("Invalid operation name!")


if __name__ == "__main__":
    '''
    // pre-define the three types of authorized vaccines
    // note: it's a poor practice to hard-code these values, but we will do this ]
    // for the simplicity of this assignment
    // and then construct a map of vaccineName -> vaccineObject
    '''

    # start command line
    print()
    print("Welcome to the COVID-19 Vaccine Reservation Scheduling Application!")

    start()
