from flask import Flask, send_file, make_response
from datetime import datetime, timedelta
import subprocess, re

app = Flask(__name__)

lastdate = ''

@app.route('/')
def hello_world():
    print("/")
    currentdate = datetime.today().strftime('%Y%m%d')
    try :
        fd = open('lastDate')  # YYYYMMDD
        lastdate = fd.read()
        fd.close()
        if currentdate > lastdate :
            print("Data update :", currentdate, '>=', lastdate)
            endDate = datetime.today().strftime('%m/%d/%Y')
            re_date = re.search("(\d\d\d\d)(\d\d)(\d\d)", lastdate)
            if re_date :
                startDate = re_date.group(2)+'/'+re_date.group(3)+'/'+re_date.group(1)
                print("ProMED interval :", startDate, endDate)
                script = 'scraping_ProMED_Avian_Influenza_affecting_mammals.py'
                print('Analyse des nouveaux posts de ProMED...')
                subprocess.run(['python3', script, startDate, endDate])
                print('...fin')
                tomorrow = datetime.today() + timedelta(days=1)
                tomorrow = tomorrow.strftime('%Y%m%d')
                fr = open('lastDate', 'w')
                fr.write(tomorrow)
                fr.close()
    except Exception as e :
        print('Error :', e)
    return send_file('carto_with_server.html')

@app.route('/file/<filename>')
def forFile(filename):
    print(filename)
    return send_file(filename)

@app.route('/data/csv')
def forCSV():
    print('csv')
    try :
        return send_file('promed Influenza.csv')
    except :
        print("promed Influenza.csv not found")
        return ''

@app.route('/data/json')
def forJSON():
    print('json')
    try :
        fd = open('promed Influenza.json')
        response = make_response(fd.read())
        response.headers['Content-Type'] = 'application/json'
        return response
    except :
        print("promed Influenza.json not found")
        response = make_response('[]')
        response.headers['Content-Type'] = 'application/json'
        return response

if __name__ == '__main__':
    app.run()



