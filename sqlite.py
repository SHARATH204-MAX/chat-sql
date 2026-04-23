import sqlite3

# Connect to sqlite
connection = sqlite3.connect("student.db")
cursor = connection.cursor()

# Drop tables if they exist to refresh schema
cursor.execute("DROP TABLE IF EXISTS STUDENT")
cursor.execute("DROP TABLE IF EXISTS DEPARTMENTS")

# Create DEPARTMENTS table
cursor.execute("""
CREATE TABLE DEPARTMENTS(
    ID INT PRIMARY KEY,
    DEPT_NAME VARCHAR(25)
)
""")

# Create STUDENT table with DEPT_ID for JOINs
cursor.execute("""
CREATE TABLE STUDENT(
    NAME VARCHAR(25),
    CLASS VARCHAR(25),
    SECTION VARCHAR(25),
    MARKS INT,
    DEPT_ID INT,
    AGE INT,
    FOREIGN KEY (DEPT_ID) REFERENCES DEPARTMENTS(ID)
)
""")

# Insert into DEPARTMENTS
cursor.execute("INSERT INTO DEPARTMENTS VALUES(1, 'Data Science')")
cursor.execute("INSERT INTO DEPARTMENTS VALUES(2, 'DEVOPS')")
cursor.execute("INSERT INTO DEPARTMENTS VALUES(3, 'CSE')")

# Insert into STUDENT
cursor.execute("INSERT INTO STUDENT VALUES('Krish', 'Data Science', 'A', 90, 1, 21)")
cursor.execute("INSERT INTO STUDENT VALUES('John', 'Data Science', 'B', 100, 1, 22)")
cursor.execute("INSERT INTO STUDENT VALUES('Mukesh', 'Data Science', 'A', 86, 1, 20)")
cursor.execute("INSERT INTO STUDENT VALUES('Jacob', 'DEVOPS', 'A', 50, 2, 23)")
cursor.execute("INSERT INTO STUDENT VALUES('Dipesh', 'DEVOPS', 'A', 35, 2, 19)")
cursor.execute("INSERT INTO STUDENT VALUES('Ankit', 'CSE', 'C', 95, 3, 21)")
cursor.execute("INSERT INTO STUDENT VALUES('Sneha', 'CSE', 'C', 88, 3, 22)")

print("The inserted records are:")
data = cursor.execute("SELECT * FROM STUDENT")
for row in data:
    print(row)

connection.commit()
connection.close()
