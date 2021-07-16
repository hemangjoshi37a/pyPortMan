# ####### CREATE A MYSQL DATABASE   ##########
# import MySQLdb
# mysqldb = MySQLdb.connect(host="localhost",user="root",password="mysql123!@#")
# mycursor = mysqldb.cursor()
# mycursor.execute("create database dbpython")


#### CONNECT TO DATABASE #######
import MySQLdb
mysqldb = MySQLdb.connect(host="127.0.0.1",user="root",password="mysql123!@#",database="dbpython")
mycursor = mysqldb.cursor()

####Create a table into dbpython database if not exists  ########
table_name = 'student'

table_exists= False
try:
    mycursor.execute(f"SHOW TABLES LIKE '{table_name}' ;")
    result=mycursor.fetchall() 
    if(len(result)>0):
        table_exists= True
        print(f'{table_name} TABLE already exists..!')
        
    if(not table_exists):
        mycursor.execute(f"create table {table_name}(roll INT,name VARCHAR(255), marks INT)")
        print(f'{table_name} TABLE created sucessfully..!')
        
except Exception as ee:
    print('Error:Unable to fetch data.' + str(ee))
    
    
### INSERT RECORD TO MYSQL #######
try:  
   mycursor.execute("insert into student values(1,'Sarfaraj',80),(2,'Kumar',89),(3,'Sohan',90)")  
   mysqldb.commit() 
   print('Record inserted successfully...')   
except:  
   mysqldb.rollback()  

### DISPLAY RECORDS ########
try:
    mycursor.execute("select * from student")
    result=mycursor.fetchall()
    for i in result:    
        roll=i[0]  
        name=i[1]  
        marks=i[2]  
        print(roll,name,marks)  
except:
    print('Error:Unable to fetch data.')  
    
#### UPDATE RECORD ###
import mysql.connector  
try:  
   mycursor.execute("UPDATE student SET name='Ramu', marks=100 WHERE roll=1")
   mysqldb.commit()  
   print('Record updated successfully...')   
except:   
   mysqldb.rollback()  

#### DELETE RECORD ####
import mysql.connector   
try:   
   mycursor.execute("DELETE FROM student WHERE roll=3")   
   mysqldb.commit()
   print('Record deteted successfully...')  
except:  
   mysqldb.rollback()  