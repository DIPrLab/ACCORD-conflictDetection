from src.sqlconnector import DatabaseQuery
from src.logextraction import extractDriveLog
from datetime import datetime, timedelta

# Method to update Activity Logs in the database

class Logupdater():
    def __init__(self, mysql, reportsAPI_service):
        self.mysql = mysql
        self.reportsAPI_service = reportsAPI_service


    def updateLogs_database(self):
        try:
            # Create DB connection
            db = DatabaseQuery(self.mysql.connection, self.mysql.connection.cursor())

            # Extract last log date from the database
            last_log_date = db.extract_lastLog_date()
            totalLogs = 0
            
            if(last_log_date != None):
                # Extract the activity logs from the Google cloud from lastlog Date
            
                activity_logs = extractDriveLog(last_log_date, self.reportsAPI_service)
                
                activity_logs.pop(0)

                # Update the log Database table when the new activities are recorded
                if(len(activity_logs) > 1):
                    new_log_date = activity_logs[0].split('\t*\t')[0]

                    # Parse the string into a datetime object
                    date_format = "%Y-%m-%dT%H:%M:%S.%fZ"
                    log_datetime = datetime.strptime(new_log_date, date_format)

                    # Subtract 4 hours
                    updated_datetime = log_datetime

                    # Format it back to a string if needed
                    updated_log_date = updated_datetime.strftime(date_format)

                    db.add_activity_logs(activity_logs)
                    db.update_log_date(updated_log_date)
                    totalLogs = len(activity_logs)-1
                    

            del db

            return totalLogs

        except LookupError as le:
            return "Error in the key or index !!\n" + str(le)
        except ValueError as ve:
            return "Error in Value Entered !!\n" + str(ve)
        except TypeError as te:
            return "Error in Type matching !!\n" + str(te)  