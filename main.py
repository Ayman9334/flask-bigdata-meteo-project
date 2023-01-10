from flask import Flask, render_template, request, redirect, url_for, send_file,session
from pymongo import MongoClient
from datetime import timedelta, date, datetime
from bson.json_util import dumps
import requests

#for matplotlib
from matplotlib import pyplot as plt
import numpy as np
plt.switch_backend('agg')

#for worcloud
from random_word import RandomWords
from wordcloud import WordCloud


# -------------------------------------------------
#                  Conections
# -------------------------------------------------
#Flask
app = Flask(__name__)
app.secret_key = 'useless'
#Mongodb
client = MongoClient()
db = client['BigData']
collection = db['BD2022']

# -------------------------------------------------
#                  Functions
# -------------------------------------------------

def daterange(date1, date2):
        for n in range(int((date2 - date1).days)):
            yield date1 + timedelta(n)

            
def checkdbforupdate(e_date = date.today()):
    s_date = collection.find().sort('date', -1).limit(1)[0]['date']
    s_date = datetime.strptime(s_date, '%Y-%m-%d').date()
    lstdates = []
    for dt in daterange(s_date, e_date):
        lstdates.append(dt.strftime("%Y-%m-%d"))
    lstdates.pop(0)
    if len(lstdates) > 0:
        for date in lstdates:
            api_get = requests.get(
                f'https://public.opendatasoft.com/api/records/1.0/search/?dataset=donnees-synop-essentielles-omm&q=&sort=date&facet=date&facet=nom&facet=temps_present&facet=libgeo&facet=nom_epci&facet=nom_dept&facet=nom_reg&refine.date={date}')
            dtapi = api_get.json()
            for record in dtapi['records']:
                fields = record['fields']
                if ("tc" in fields) and ("ff" in fields) and ("u" in fields):
                    dtdict = {
                        "nom": fields['nom'],
                        "date": fields['date'][0:10],
                        "huere": fields['date'][11:16],
                        "temp": round(fields['tc'], 1),
                        "Humidite": fields['u'],
                        "vvma": fields['ff']
                    }
                    collection.insert_one(dtdict)
                print(f'{date} data downloaded succesfuly')


def apitodb(nom, date):
    api_get = requests.get(
        f'https://public.opendatasoft.com/api/records/1.0/search/?dataset=donnees-synop-essentielles-omm&q=&sort=date&facet=date&facet=nom&facet=temps_present&facet=libgeo&facet=nom_epci&facet=nom_dept&facet=nom_reg&refine.date={date}&refine.nom={nom}')
    dtapi = api_get.json()
    rec = dtapi['records']
    if len(rec)==0: return True
    for y in rec:
        dtdict = {
            "nom": nom,
            "date": date,
            "huere": y['fields']['date'][11:16],
            "temp": round(y['fields']['tc'], 1),
            "Humidite": y['fields']['u'],
            "vvma": y['fields']['ff']
        }
        collection.insert_one(dtdict)
    return False


def tablebord(date, nom):
    lstoflbl = ['temp','Humidite','vvma']
    for lbl in lstoflbl:
        hr = []
        ylbl = []
        for dtdb in collection.find({"date": date, "nom": nom}).sort("huere"):
            hr.append(dtdb["huere"])
            ylbl.append(dtdb[lbl])
        plt.plot(hr, ylbl, color='g', linestyle='dashed',
                 marker='o')
        plt.xlabel('Heure',fontsize = 15)
        plt.ylabel(lbl,fontsize = 15)
        plt.ylim(ymin=0)
        plt.grid()
        plt.legend()
        plt.ioff()
        plt.savefig(f'static/Jour{lbl}.png')
        plt.close()

    

#-----------------Check for update-----------------

# checkdbforupdate()

# -------------------------------------------------
#                  Main Page
# -------------------------------------------------


@app.route('/')
def main():
    today = date.today()
    todaydt = today.strftime("%Y-%m-%d")
    return render_template('main.html', todaydt=todaydt)


# -------------------------------------------------
#                  Table Page
# -------------------------------------------------


@app.route('/table', methods=['GET', 'POST'])
def table():
    if request.method == 'POST':
        session['date'] = request.form.get('date')
        session['nom'] = request.form.get('nom').upper()
        date = session['date']
        nom = session['nom']
        if collection.find_one({"nom": nom, "date": date}) == None: 
            check = apitodb(nom, date)
            if check : return render_template('errorpage.html')
        
        tablebord(date, nom)
        listDict = collection.find({"date": date, "nom": nom}).sort("huere")

        return render_template('datapage.html', listDict=listDict, nom=nom, date=date)

    return redirect(url_for("main"))


# -------------------------------------------------
#                download links
# -------------------------------------------------

#------------------JSON FILE-----------------------
@app.route('/downloadfile')
def download():
    date = session['date']
    nom = session['nom']
    lta = list(collection.find({'date': date,'nom': nom}))
    json_data = dumps(lta, indent=2)
    with open(r"data/data.json", 'w') as json_file:
        json_file.write(json_data)
    return send_file(r'data/data.json', as_attachment=True)

#----------------WORDCLOUD-------------------------
@app.route('/downloadwc')
def downloadwc():
    r = RandomWords()
    with open(r'data/txt.txt', 'w') as f:
        for n in range(25):
            f.write(r.get_random_word())
            f.write('\n')
    
    df = open(r'data/txt.txt', 'r').read()
    wc = WordCloud(background_color = 'white', width = 1000, height = 1000)
    wc.generate_from_text(df)
    wc.to_file(r'static/wordcloud.png')

    return send_file(r'static/wordcloud.png', as_attachment=True)



#----------RUN------------
if __name__ == '__main__':
    app.run(debug=1)