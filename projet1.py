import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import matplotlib.pyplot as plt
from unidecode import unidecode

DOWNLOAD_DELAY = 3
USER_AGENT = 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'

def connexion(login, mdp, url, driver) :
    """connexion au site de polytech (url) avec le login et mot de passe, puis récupération des données nécessaires"""
    driver.get(url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="tarteaucitronAlertBig"]/button[2]'))).click()
    # entrée du login
    loginInput = driver.find_element(By.XPATH, "/html/body/section[3]/div/div/div/div/div/form/fieldset/input[1]")
    loginInput.send_keys(login)
    # entrée du mdp
    mdpInput = driver.find_element(By.XPATH, "/html/body/section[3]/div/div/div/div/div/form/fieldset/input[2]")
    mdpInput.send_keys(mdp)
    #ouverture de la bonne interface
    driver.find_element(By.XPATH, "/html/body/section[3]/div/div/div/div/div/form/fieldset/input[3]").click()
    driver.get(url)
    # choix des options : IDU 2021-2025
    driver.find_element(By.XPATH, "/html/body/div[2]/div/div/div/div[2]/div/div[5]/div[2]/div/div/form/ul/li[1]/input[2]").click()
    driver.find_element(By.XPATH, "/html/body/div[2]/div/div/div/div[2]/div/div[5]/div[2]/div/div/form/ul/li[2]/div/input[11]").click()
    driver.execute_script("window.scrollTo(0, 100)")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH,"/html/body/div[2]/div/div/div/div[2]/div/div[5]/div[2]/div/div/form/div[2]/button[1]"))).click()
    listProf(listUrl(driver), driver) #recuperation des donnees (voir detail des fonctions)
    driver.quit() #fermeture de la fenetre

def listUrl(driver):
    """ Récupère le lien pour chaque module et renvoie la liste de ces liens """
    list_url = []
    # 2 classes différentes correspondent aux div de chaque module : on récupère le nombre pour pouvoir les parcourir
    nbModules = len(driver.find_elements(By.XPATH, "/html/body/div[2]/div/div/div/div[2]/div/div[5]/div[3]/div/div[2]/div[2]/div[@class='item separateurUE ']")) 
    nbModules += len(driver.find_elements(By.XPATH, "/html/body/div[2]/div/div/div/div[2]/div/div[5]/div[3]/div/div[2]/div[2]/div[@class='item ']")) 
    for i in range(1, nbModules) : 
        #parcours du nombre de module et ajout de l'url qui lui correspond à la liste
        module = driver.find_element(By.XPATH,  f'/html/body/div[2]/div/div/div/div[2]/div/div[5]/div[3]/div/div[2]/div[2]/div[{i}]/div[2]/ul/li[4]/a')
        url_module = module.get_attribute('href')
        list_url.append(url_module)
    return list_url

def listProf(listUrls, driver) :
    """ Recupere les mails des profs pour chaque module, puis trie les informations et ajoute la liste des profs au json (voir fonctions suivantes) 
    parametres :
        listUrls : liste des urls des différents modules"""
    allProf = [] #initialisation liste des profs
    for url in listUrls :
        try :
            time.sleep(2)
            driver.execute_script("window.open('');") # ouverture du lien dans une nouvelle fenêtre
            handles = driver.window_handles
            driver.switch_to.window(handles[-1])
            driver.get(url)
            # recuperation des mails
            mail = driver.find_element(By.XPATH,  '/html/body/div[2]/div/div/div/div[2]/div/div[5]/div[3]/div/div[2]/div[2]/div[3]/div[2]/div[2]').text
            addProf(mail, allProf, driver) # ajout du prof a la liste a partir du mail
            driver.close() # fermeture du nouvel onglet
            driver.switch_to.window(handles[0]) # on retourne à l'onglet initial
        except NoSuchElementException:
            #Stages : erreur car pas d'heures de présentiel
            # Pas nécessaire ici car on cherche à récupérer les heures de présentiel des profs
            # on referme l'onglet :
            driver.close()
            driver.switch_to.window(handles[0])
            continue

    # ecriture dans le fichier json
    with open("Ressources/Infos_profs_IDU.json","w") as f:
            json.dump(allProf,f, indent=3)

def addProf(mail, listProf, driver) :
    """ ajout du prof à la liste, en prenant en compte s'ils sont déjà présents"""
    mail = cleanMail(mail) # nettoyage du mail récupéré
    if type(mail) is list :
        # apres nettoyage, certains mails sont sous forme de liste
        for m in mail :
            if getName(m)!=None :
                prenom = cleanName(getName(m)[0])
                nom = cleanName(getName(m)[1])
                newprof = createProf(driver, prenom, nom, mail) # creation dict avec informations du prof
                #print(newprof)
                sortProf(listProf, newprof, driver)
                #print(listProf)
    else :
        if getName(mail)!=None :
        # print(mail)
            prenom = cleanName(getName(mail)[0])
            nom = cleanName(getName(mail)[1])
            newprof = createProf(driver, prenom, nom, mail)
            # print(newprof)
            sortProf(listProf, newprof, driver)
            # print(listProf)

def createProf(driver, prenom, nom, mail) :
    """ retourne un dictionnaire correspondant aux informations d'un prof : nom, prenom, liste des modules, total d'heures"""
    newprof = {'prenom' : prenom, 'nom' : nom}
    module = driver.find_element(By.XPATH,  '/html/body/div[2]/div/div/div/div[2]/div/div[5]/div[3]/div/div[2]/div[1]/div[2]').text
    nbHeures = getNbHeuresPresentiel(driver)
    newprof['listModule'] = [moduleDict(cleanMail(mail), module, nbHeures)]
    newprof['totalH'] = nbHeures/(newprof['listModule'][0]['nbProfs'])
    return newprof

def sortProf(listProf, newprof, driver) :
    inList = False
    #prof deja present
    for prof in listProf :
        #print(prof)
        if prof['prenom'] == newprof['prenom'] and prof['nom'] == newprof['nom'] :
            print('prof existant')
            inList = True
            newmodule = newprof['listModule'][0]
            prof['listModule'].append(newmodule) #ajout du nouveau module
            prof['totalH'] = prof['totalH'] + newmodule['nbHeures']/newmodule['nbProfs'] # mise a jour du nombre d'heures
            break

    # prof pas encore present dans la liste
    if not(inList) :
        print('nouveau prof')
        print(newprof)
        listProf.append(newprof) #ajout à la liste
        newprof["articles"] = getArticles(newprof, driver) # récupération de ses articles

def getArticles(prof, driver) :
    """récupération du lien et du nombre d'articles du prof en parametre"""
    driver.execute_script("window.open('');") # ouverture du lien dans une nouvelle fenêtre
    handles = driver.window_handles
    driver.switch_to.window(handles[-1])
    prenom = prof['prenom']
    nom = prof['nom']
    driver.get(f"https://hal.science/search/index?q={prenom}+{nom}") #recherche du prof dans hal
    try :
        # nb articles
        nbArticles = cleanResult(driver.find_element(By.XPATH,"/html/body/main/section/section[2]/div[1]/div[1]/span").text)
        articles = findAuteur(int(nbArticles), prenom, nom, driver)
        if articles == {} : #cas ou on obtient un résultat pour le prof, mais aucun article de lui
            articles = None
    except NoSuchElementException :
        #pas de resultat : le prof n'a pas d'article
        articles = None
        pass
    driver.close() # fermeture du nouvel onglet
    driver.switch_to.window(handles[1]) # on retourne à l'onglet initial
    return articles


def findAuteur(nbArticles, prenom, nom, driver) :
    """renvoie le nombre d'articles et le lien des articles d'un prof"""
    articles = {}
    for i in range(1, 30) :
        time.sleep(2)
        auteurs = driver.find_elements(By.XPATH, f"/html/body/main/section/section[2]/table/tbody/tr[{i}]/td[3]/span[1]/a")
        for auteur in auteurs :
            print(auteur.text)
            cleanAuteur = unidecode(auteur.text).lower()
            if prenom.lower() in cleanAuteur and nom.lower() in cleanAuteur :
            # on verifie si le nom et prenom sont present dans l'intitule d'un auteur
            # on ne peut pas juste verifier que l'intitulé de l'auteur est simplement nom + prenom car certains ont un 2e prenom
            # exemple : Abdourrahmane Mahamane Atto
            # on compare avec la version unidecode en minuscule de l'intitule de l'auteur pour enlever les erreurs d'accents et de majuscule
                urlAuteur = auteur.get_attribute('href')
                nb = getNbArticles(urlAuteur, driver)
                articles = {"nbArticles" : nb, "url" : urlAuteur}
                print(articles)
                break
        if articles != {} :
            break
    return articles

def getNbArticles(url, driver) :
    """renvoie le nombre d'articles dans hal pour une url"""
    driver.execute_script("window.open('');") # ouverture du lien dans une nouvelle fenêtre
    handles = driver.window_handles
    driver.switch_to.window(handles[-1])
    driver.get(url)
    res = int(cleanResult(driver.find_element(By.XPATH,"/html/body/main/section/section[2]/div[1]/div[1]/span").text))
    driver.close() # fermeture du nouvel onglet
    driver.switch_to.window(handles[2]) # on retourne à l'onglet initial
    return res

def cleanMail(mail) :
    """Renvoie une liste de mail si plusieurs mails sont présents dans le texte en parametre"""
    if ' et' in mail :
        mail = mail.split(' et')
    elif ';' in mail :
        mail = mail.split(';')
    elif ',' in mail:
        mail = mail.split(',')
    return mail

def cleanResult(result) :
    " permet de récupérer uniquement le nombre de résultats sur hal"
    res = result.split()
    return res[0]

def moduleDict(mail, module, nbHeures) :
    """renvoie un dictionnaire correspondant aux informations d'un module"""
    mail = cleanMail(mail)
    # cas ou il y a plusieurs profs responsables
    if type(mail) is list : 
        nbProfs = len(mail)
    else :
        nbProfs = 1

    return {'module' : module, 'nbHeures' : nbHeures, 'nbProfs' : nbProfs}


def getName(mail) :
    """renvoie une liste dont le premier élément correspond au prenom et le 2e au nom du prof"""
    if "@univ-smb.fr" in mail :
        mail = mail.replace('@univ-smb.fr', "")
        name = mail.split('.')
    elif "@univ-savoie.fr" in mail :
        mail = mail.replace('@univ-savoie.fr', "")
        name = mail.split('.')
    else :
        return None
    return name

def cleanName(name) :
    """permet d'avoir le même format pour tout les noms"""
    name = name.strip()
    return name.capitalize()

def getNbHeuresPresentiel(driver):
    """retourne le nombre d'heures en presentiel qui est renseigné sur le site"""
    divNbHeures = driver.find_elements(By.XPATH, "/html/body/div[2]/div/div/div/div[2]/div/div[5]/div[3]/div/div[2]/div[2]/div[5]/div[@class='field nbHeures']")
    nbHeures = driver.find_element(By.XPATH, f'/html/body/div[2]/div/div/div/div[2]/div/div[5]/div[3]/div/div[2]/div[2]/div[5]/div[{len(divNbHeures)-1}]/div[2]').text
    return float(nbHeures)


#### REPRESENTATION GRAPHIQUE ####

def graph(jsonPath) :
    """affichage de deux graphiques : volume horaire pour chaque prof et nombre d'articles pour ceux qui en ont"""
    with open(jsonPath,"r") as f:
        data = json.load(f)

    sorted_data = sorted(data, key=lambda d: d['nom']) #trié par ordre alphabetique des noms
    
    # graphique des heures
    names1 = []
    values1 = []
    colors1 = []
    graphHeures(sorted_data, names1, values1, colors1) 

    #graphique des articles
    names2 = []
    values2 = []
    colors2 = []
    graphArticles(sorted_data, names2, values2, colors2)

    #creation des 2 figures
    fig, (f1, f2) = plt.subplots(1, 2, figsize=(10,20))
    fig.suptitle("Heures de cours en présentiel et nombre d'articles des profs d'IDU")
    f1.barh(names1, values1, color = colors1)
    f2.barh(names2, values2, color = colors2)
    plt.subplots_adjust(wspace=0.5)
    plt.show()

def graphHeures(data, names, values, colors) :
    """permet de recuperer les valeurs des abscisses et des oronnees pour le graphe des heures, ainsi que la couleur de chaque barre"""
    maxValue = getMaxValue1(data, 'totalH') # valeur maximum(utile pour le gradient de couleur)
    for prof in data :
        name = prof['prenom'] + ' ' + prof['nom']
        value = prof['totalH']
        names.append(name)
        values.append(value)
        colors.append(gradient(value, maxValue))

def graphArticles(data, names, values, colors) :
    """permet de recuperer les valeurs des abscisses et des oronnees pour le graphe des articles, ainsi que la couleur de chaque barre"""
    maxValue = getMaxValue2(data, 'articles', 'nbArticles')
    print(maxValue)
    for prof in data :
        if prof['articles'] != None :
            name = prof['prenom'] + ' ' + prof['nom']
            value = prof['articles']['nbArticles']
            names.append(name)
            values.append(value)
            colors.append(gradient(value, maxValue))

def getMaxValue1(data, key1) :
    """renvoie la valeur maximum d'un dictionnaire pour la cle key1"""
    allValues = []
    for e in data :
        value = e[key1]
        allValues.append(value)

    return max(allValues)

def getMaxValue2(data, key1, key2) :
    """renvoie la valeur maximum d'un dictionnaire pour la cle key1"""
    allValues = []
    for e in data :
        print(e)
        if e[key1] != None :
            value = e[key1][key2]
            allValues.append(value)

    return max(allValues)

def gradient(value, maxvalue) :
    n = maxvalue/510
    pos = value/n
    print(f"pos : {pos}")
    g = 255
    r = 0
    if pos <= 255 :
        r = pos
    else :
        g = g - (pos-255)
        r = 255
    return (r/255, g/255, 0)


if __name__ == "__main__" :

    # driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    url = "https://www.polytech.univ-smb.fr/intranet/scolarite/programmes-ingenieur.html"
    login = ""
    mdp = ""
    # connexion(login, mdp, url, driver)
    graph("Ressources/Infos_profs_IDU.json")