# Author : Pierre Pompidor
# Date : 16/06/2023

import pandas as pd
import sys, json, copy, re, requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time, datetime
import csv

months = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06','Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
criterias = ['vsi_event_id', 'source', 'wahis_id', 'adis_id', 'promed_id', 'promed_archive_number', 'subpost', 'source_fr_id', 'disease', 'region', 'country', 'admin1', 'admin2', 'admin3', 'admin4', 'admin5', 'latitude', 'longitude', 'prim_sec_outb', 'serotype', 'start_date', 'conf_date', 'event_date', 'report_date', 'last_modification_date', 'comp_fr', 'comp_en', 	'species', 'wild_type', 'nb_susceptible', 'nb_cases', 'mortality', 'nb_dead', 'comments', 'production', 'epi_unit', 'test_cat', 'test_name', 'link', 'link2']
disease = "Influenza"
species = {}
vernacularNames = {'EN': {}, 'SP': {}, 'FR': {}}
continents = {}
countries = {}
directedResearch = {'serotype': ['H3N8', 'H5','H5N1', 'H5N3', 'H5N5', 'H5N6', 'H5N8', 'H7', 'H7N3', 'H9N2', 'HPAI'],
    'comp_fr': ['captif', 'commercial', 'domestique', 'sauvage', 'zoo'],
    'comp_en': ['backyard', 'captive', 'commercial', 'domestic', 'wild', 'zoo']
}

eventsJson = []

def normalizedDate(date) :
    # 29 May 2022 => 20220529
    res = re.search("(\d\d) (.+) (\d\d\d\d)", date)
    if res :
        return res.group(3)+months[res.group(2)]+res.group(1)
    print("Pb de date :", date)
    return date
    
def speciesImportation() :
    with open("species.json") as fd :
        species = json.load(fd)
        fd.close()
    species.pop('Homo sapiens', '')
    for sp in species :
        family = ''
        if 'family' in species[sp] : family = species[sp]['family']
        for name in species[sp]['EN'] :
            if name != '' : vernacularNames['EN'][name.lower()] = [family.lower()]  # TO DO en amont
        for name in species[sp]['SP'] :
            if name != '' : vernacularNames['SP'][name.lower()] = [family.lower()]  # TO DO en amont
        for name in species[sp]['FR'] :
            if name != '' : vernacularNames['FR'][name.lower()] = [family.lower()]  # TO DO en amont
    with open("mammals") as fd :
        for line in fd :
            data = line[:-1].lower().replace(', ',',').split(',')
            if len(data) == 4 :
                english_names = data[0].split('/')
                spanish_names = data[1].split('/')
                french_names = data[2].split('/')
                families = data[3].split('/')
                for name in english_names :
                    if name not in vernacularNames['EN'] : vernacularNames['EN'][name] = families
                for name in spanish_names :
                    if name not in vernacularNames['SP'] : vernacularNames['SP'][name] = families
                for name in french_names :
                    if name not in vernacularNames['FR'] : vernacularNames['FR'][name] = families
        fd.close()
    #print(species)
    print(len(species), "scientific names of species")
    print(len(vernacularNames['EN']), "engish names of species/families")
    print(len(vernacularNames['SP']), "spanish names of species/families")
    print(len(vernacularNames['FR']), "french names of species/families")
    return species

def geographicalEntityImportation() :
    with open("continents") as fd :
        for line in fd :
            continents[line[:-1].lower()] = []
        fd.close()
        #print(len(continents), "imported continent names")
    with open("countryListLatLon") as fd :
        for line in fd :
            line = re.sub(' / ','/', line)
            data = line[:-1].lower().split('/')
            for d in data[0:3] :
                data2 = d.split(',')
                for d2 in data2 :
                    countries[d2] = (data[3], data[4])  # lat / lon
        fd.close()
        print(len(countries), "country names")

def subjectGeographicalEntityIdentification(infos) :
    continentList = []
    countryList = []
    for ge in continents :
        if re.search(r'\b'+ge+r'\b', infos, re.IGNORECASE) :
            continentList.append(ge.lower())
    for ge in countries :
        if re.search(r'\b'+ge+r'\b', infos, re.IGNORECASE) :
            countryList.append(ge.lower())
    print(countryList)
    return continentList, countryList

def subjectSpeciesIdentification(infos, lang) :
    results = []
    infos.lower()
    for name in vernacularNames[lang] :
        if re.search(r'\b'+name+r's?\b', infos) :
            print(name, "=> in subject / sub-subject")
            results.append(name)
    return results 

def subjectParsing(result, text, headerSerotypes, headerSpecies) :
    # Subject: PRO/AH/EDR> Avian Influenza (41): Americas (Chile) marine otter
    # UK (England): grey seal, harbor seal, red fox, HPAI H5N8  <= subPost
    # Exception : directly the date for several subpots
    print("subjectParsing()")
    lang = 'EN'
    if re.search(r"/ESP\S*?>", text) : lang = 'SP'
    if re.search(r"/FR\S*?>", text) : lang = 'FR'
    print("LANGUAGE :", lang)
    speciesInSubject = subjectSpeciesIdentification(text, lang)
    print("headerSpecies >>>", headerSpecies)
    print("result['species'] >>>", result['species'])
    print("speciesInSubject >>>", speciesInSubject)
    speciesList = []
    result['species'] = []
    if speciesInSubject != [] :
        if headerSpecies != [] :
            for sp in speciesInSubject : 
                # TO DO : verify marine mammal
                if headerSpecies[0] in ['mammal', 'mamífero', 'mammifère', 'marine mammal', 'mamífero marinero', 'mammifère marin', 'cetacean', 'cetáceo', 'cétacé', 'carnivore', 'carnívoro'] or sp in headerSpecies :
                    speciesList.append(sp)  # POST and SUBPOST !
        else : speciesList = speciesInSubject
    else :
        speciesList = headerSpecies
    if speciesList != [] :
        print("ICI")
        # deletion of a species name included in another
        for sp1 in speciesList :
            found = False
            for sp2 in speciesList :
                if sp1 != sp2 and re.search(sp1, sp2) : found = True
            if not found : result['species'].append(sp1)
        print("Après néttoyage de result['species'] :", result['species'])
        for criteria in directedResearch :
            for v in directedResearch[criteria] :
                if re.search(v, text) :
                    if result[criteria] != '' :
                        result[criteria] += ','
                    print("Extraction de", v, "de l'entête", criteria)
                    result[criteria] += v
        if result['serotype'] == '' :
            result['serotype'] = headerSerotypes
        regions, result['country'] = subjectGeographicalEntityIdentification(text)
        for ge1 in regions :
            for ge2 in regions :
                if ge1 != ge2 and re.search(ge1, ge2) and not ge1 in regions :
                    regions.remove(ge1)
        result['region'] = regions
    return result, lang

def headerParsing(result, post_text) :
    """
    Published Date: 2023-02-23 00:07:46 CET
    Subject: PRO/AH/EDR> Avian influenza (32): Americas (Peru) HPAI H5N1, pelican, sea lion
    Archive Number: 20230222.8708539
    """
    print(post_text)
    lang = 'EN'  # possibly modify in subjectParsing()
    subject = ''
    re_subject = re.search(r"Subject:\s(?P<subject>.*)", post_text)
    if re_subject :
        subject = re_subject.group("subject")
        result, lang = subjectParsing(result, subject, [], [])
        print("Species :", result['species'])
    promed_date_match = re.search(r"Published Date:\s(?P<date>.*)", post_text)
    if promed_date_match :
        #print(promed_date_match.group("date"))
        result["report_date"] = promed_date_match.group("date")
        #result["promedDate"] = api.parse_promed_pub_datetime(promed_date_match.group("date"))
    archive_match = re.search(r"Archive Number: (?P<num>.*)", post_text)
    if archive_match :
        result["promed_archive_number"] = archive_match.group("num")
    return result, lang, subject

def geonamesCheckingADM1(r, ge) :
    lat = ''; lng = ''
    if 'geonames' in r :
        for geoname in r['geonames'] :
            if 'fcode' in geoname and geoname['fcode'] == 1 :
                if 'lat' in geoname and 'lng' in geoname :
                    lat = geoname['lat']
                    lng = geoname['lng']
                print(ge, '>>> ADM1 de', geoname['countryName'], 'avec', lat, ':', lng)
                return True, lat, lng, geoname['countryName']
    return False, lat, lng, ''

def geonamesChecking(country, r, ge) :
    #url = "http://api.geonames.org/hierarchy?geonameId=2649994&username=pierrepompidor"
    #print(ge, 'dans', country, "?")
    if 'geonames' in r :
        for geoname in r['geonames'] :
            if 'fcode' in geoname and 'countryName' in geoname :
                for suffixe in [1, 2, 3, 4, 5] :
                    adm = 'ADM'+str(suffixe)
                    if geoname['fcode'] == adm and geoname['countryName'].lower() == country :
                        lat = ''; lng = ''
                        if 'lat' in geoname and 'lng' in geoname :
                            lat = geoname['lat']
                            lng = geoname['lng']
                        print(ge, '>>> ADM'+str(suffixe)+' de', geoname['countryName'], 'avec', lat, ':', lng)
                        return suffixe, lat, lng
                    if  geoname['fcode'] == adm and geoname['countryName'] == 'United States' and country in ['usa','u.s.a.'] :
                        lat = ''; lng = ''
                        if 'lat' in geoname and 'lng' in geoname :
                            lat = geoname['lat']
                            lng = geoname['lng']
                        print(ge, '>>> ADM'+str(suffixe)+' de', country, 'avec', lat, ':', lng)
                        return suffixe, lat, lng
                    if  geoname['fcode'] == adm and geoname['countryName'] == 'United Kingdom' and country in ['uk', 'u.k.'] :
                        lat = ''; lng = ''
                        if 'lat' in geoname and 'lng' in geoname :
                            lat = geoname['lat']
                            lng = geoname['lng']
                        print(ge, '>>> ADM'+str(suffixe)+' de', country, 'avec', lat, ':', lng)
                        return (suffixe, lat, lng)
    return (0, '', '')

def adminParsing(subjectCountries, headerCountries, text) :
    # headerCountries : pays de l'entête globale
    # subjectCountries : pays de l'entête la plus proche
    #print(text)
    #rep = input("Arrêt")
    headers = {'user-agent': 'Mozilla/5.0'}
    countryList = []
    admins = [[], [], [], [], []]
    latLon = [[], [], [], [], []]
    if subjectCountries != [] :
        countryList = subjectCountries
        print(subjectCountries, "=> in post -1")
    else :
        if len(headerCountries) == 1 :
            countryList = headerCountries
            print(headerCountries, "=> in post -2")
    ges = re.findall(r"[\w,][ (:]([A-Z][a-z]+)([ -][A-Z][a-z]+)?\b", text, flags=re.DOTALL)
    garbage = ['Acuicultura', 'Agricultura', 'Agricultural', 'Agriculture', 'Aquaculture', 'Animal', 'Apr', 'April', 'Associated', 'Broadcasting', 'Canidae', 'Cases', 'Centers', 'Control', 'Database', 'Deaths', 'Dec', 'December', 'Department', 'Departemento', 'Development', 'Disease', 'Dr', 'Economy', 'Feb', 'February', 'Fisheries', 'Following', 'Fri', 'Friday', 'Gene', 'Health', 'Highly', 'In', 'Inf', 'Infectious', 'Institute', 'Jan', 'January','Journal', 'Jun', 'June', 'Killed', 'Laboratory', 'Mar', 'Mars', 'May', 'Metropolitan', 'Minister', 'Ministry', 'Mon', 'Monday', 'Nacional', 'National', 'Natural', 'Nov', 'November', 'Number', 'On', 'One', 'Oct', 'October', 'Our', 'Pesca', 'Phocidae', 'Plant', 'Positive', 'Poultry', 'Press', 'Prevention',  'Reserve', 'Reverse', 'Result', 'Sanitaire', 'Sat', 'Saturday', 'Secretary', 'Sep', 'September', 'Society', 'Slaughtered', 'Spectrum', 'Sun', 'Sunday', 'Susceptible', 'Test', 'The', 'This', 'Tourism', 'Tue', 'Tuesday', 'Undersecretary', 'Vaccinated', 'Vet']
    for ge in ges :
        if ge[0] not in garbage :
            g1 = ge[0].lower()
            g2 = ge[1].lower()
            nge = g1+g2
            url = "http://api.geonames.org/search?name_equals="+nge+"&type=json&username=pierrepompidor"
            rnge = requests.post(url, headers=headers).json()
            rg1 = []
            #if nge == 'sapporo' : print(">>>>>>>>>>>>>>>>>>> sapporo <<<<<<<<<<<<<<<<<<<<<")
            if g1 != nge :
                url = "http://api.geonames.org/search?name_equals="+g1+"&type=json&username=pierrepompidor"
                rg1 = requests.post(url, headers=headers).json()
            if subjectCountries == [] :
                if headerCountries != [] :
                    for country in headerCountries :
                        adminNum, lat, lng = geonamesChecking(country, rnge, nge)
                        if adminNum != 0 and nge not in admins[adminNum-1] :
                            admins[adminNum-1].append(nge)
                            latLon[adminNum-1].append([lat, lng, country])
                            print(nge, "=> in post 0")
                            if country not in countryList :
                                countryList.append(country)
                                print(country, "=> in post 1")
                        elif g1 != nge :
                            adminNum, lat, lng = geonamesChecking(country, rg1, g1)
                            if adminNum != 0 and g1 not in admins[adminNum-1] :
                                admins[adminNum-1].append(g1)
                                latLon[adminNum-1].append([lat, lng, country])
                                print(g1, "=> in post 2")
                                if country not in countryList :
                                    countryList.append(country)
                                    print(country, "=> in post 3")
                else :  # no countries in the headers
                    if nge in countries :
                        countryList.append(nge)
                        print(nge, "=> in post 4")
                    elif g1 in countries :
                        countryList.append(g1)
                        print(g1, "=> in post 5")
            else :
                for country in subjectCountries :
                    adminNum, lat, lng = geonamesChecking(country, rnge, nge)
                    if adminNum != 0 and nge not in admins[adminNum-1] :
                        admins[adminNum-1].append(nge)
                        latLon[adminNum-1].append([lat, lng, country])
                        print(nge, "=> in post 6")
                    elif g1 != nge :
                        adminNum, lat, lng = geonamesChecking(country, rg1, g1)
                        if adminNum != 0 and g1 not in admins[adminNum-1] :
                            admins[adminNum-1].append(g1)
                            latLon[adminNum-1].append([lat, lng, country])
                            print(g1, "=> in post 7")
    # second pass if there is no country name in the two headers and the body
    if countryList == [] :
        for ge in ges :  
            if ge[0] not in garbage :
                g1 = ge[0].lower()
                g2 = ge[1].lower()
                nge = g1+g2
                url = "http://api.geonames.org/search?name_equals="+nge+"&type=json&username=pierrepompidor"
                rnge = requests.post(url, headers=headers).json()
                rg1 = []
                if g1 != nge :
                    url = "http://api.geonames.org/search?name_equals="+g1+"&type=json&username=pierrepompidor"
                    rg1 = requests.post(url, headers=headers).json()
                if nge not in admins[0] :
                    bool, lat, lng, country = geonamesCheckingADM1(rnge, nge)
                    if bool :
                        admins[0].append(nge)
                        latLon[0].append([lat, lng, country])
                        print(nge, "=> in post 8")
                else :
                    if g1 not in admins[0] :
                        bool, lat, lng, country = geonamesCheckingADM1(rg1, g1)
                        if bool :
                            admins[0].append(g1)
                            latLon[0].append([lat, lng, country])
                            print(g1, "=> in post 9")
    return (countryList, admins, latLon)

def speciesParsing(speciesNames, text, lang) :
    # speciesNames : 
    # species : global collection
    sps = re.findall(r"_(.+?)_", text, flags=re.DOTALL)
    nsps = [sp.lower().capitalize() for sp in sps]
    nspecies = []
    if len(speciesNames) == 1 and speciesNames[0] in ['marine mammal', 'mamífero marinero', 'mammifère marin'] :
        print("Marine species :")
        for name in vernacularNames[lang] :
            if name not in nspecies and re.search(r"\b"+name+r"s?\b", text, re.IGNORECASE) :
                for family in vernacularNames[lang][name] :
                    if family in vernacularNames[lang][speciesNames[0]] :
                        boolScientificName = False
                        for scientificName in nsps :
                            if scientificName in species :
                                for name2 in species[scientificName][lang] :
                                    if name == name2.lower() :
                                        nspecies.append(name+' ('+scientificName+')')
                                        nsps.remove(scientificName)
                                        boolScientificName = True
                        if not boolScientificName : nspecies.append(name)
                        print(name, "=> in post / subpost")
    elif len(speciesNames) == 1 and speciesNames[0] in ['mammal', 'mamífero', 'mammifère'] :
        print("All species :")
        for name in vernacularNames[lang] :
            if name not in nspecies and re.search(r"\b"+name+r"s?\b", text, re.IGNORECASE) :
                boolScientificName = False
                for scientificName in nsps :
                    if scientificName in species :
                        for name2 in species[scientificName][lang] :
                            if name == name2.lower() :
                                nspecies.append(name+' ('+scientificName+')')
                                nsps.remove(scientificName)
                                boolScientificName = True
                if not boolScientificName : nspecies.append(name)
                print(name, "=> in post / subpost")
    else :
        for name in speciesNames :
            boolScientificName = False
            for scientificName in nsps :
                if scientificName in species :
                    for name2 in species[scientificName][lang] :
                        if name == name2.lower() :
                            print(name, '<=species=>', scientificName)
                            nsps.remove(scientificName)
                            nspecies.append(name+' (' + scientificName + ')')
                            boolScientificName = True
            if not boolScientificName : nspecies.append(name)
        if nsps != [] :  # not direct correspondance => indirect search using families  
            for name in speciesNames :
                if not re.search('\(', name) :
                    for scientificName in nsps :
                        if scientificName in species :
                            for family in vernacularNames[lang][name] :
                                if family == species[scientificName]['family'] :
                                    print(name, '<=family=>', scientificName)
                                    nspecies.append(name+' (' + scientificName + ')')
    return nspecies

def bodyParsingByPost(result, headerSerotypes, headerSpecies, headerCountries, text, subPost, lang, subject, promed_archive_number, promed_url) :
    """
    Date: Tue 21 Feb 2023 9:31 AM PET
    Source: KFGO, Reuters report [edited]
    https://kfgo.com/2023/02/21/bird-flu-kills-sea-lions-and-thousands-of-pelicans-in-perus-protected-areas/
    

    Bird flu has killed tens of thousands of birds, mostly pelicans, and at least 716 sea lions in protected areas across Peru, the authorities said, as the H5N1 strain spreads throughout the region.
    """
    """
    ...
    [1] UK (England): grey seal, harbor seal, red fox, HPAI H5N8
    Date: Mon 15 Mar 2021
    Source: OIE-WAHIS [edited]
    https://wahis.oie.int/#/report-info?reportId=30629
    ...
    Date of start of the event: 21 Nov 2020
    Date of confirmation of the event: 26 Jan 2021
    Species / Susceptible / Cases / Deaths / Killed and disposed of / Slaughtered-Killed for commercial use / Vaccinated
    Gray seal (_Halichoerus grypus_): Phocidae-Carnivora / - / 1 / 0 / 1 / 0 / 0
    Harbor seal (_Phoca vitulina_): Phocidae-Carnivora / - / 4 / 1 / 3 / 0 / 0
    Red fox (_Vulpes vulpes_): Canidae-Carnivora / - / 1 / 1 / 0 / 0 / 0
    """
    lines = text.split("\n")
    subpost_header = ''
    if subPost :
        subpost_header = lines[0]
        print("Subpost : analysis of", subpost_header)
        result, lang = subjectParsing(result, lines[0], headerSerotypes, headerSpecies)
    for line in lines :
        res = re.search(r"^(Date|Fecha)\s*:\s+(.*?\d\d\d\d)", line)
        if res :
            print("Date : ", res.group(2))
            result["event_date"] = res.group(2)
        else :
            res = re.search(r"^Source:\s+(.+)", line)
            if res :
                pass # cette source n'est pas celle qui doit être mise dans l'attribut "source"
                #print("Source : ", res.group(1))
                #result["source"] = res.group(1)
            else :
                res = re.search(r"^(https?:.+)", line)
                if res :
                    #print("http :", res.group(1))
                    result["link2"] = res.group(1)
                else :
                    res = re.search(": .+ / .+ / \d+ / (\d+) / \d+ / \d+ / \d+", line)
                    if res and int(res.group(1)) > 0 :
                        result["mortality"] = "yes"
                    else :
                        res = re.search("(\bdie\b|\bdied\b|\bfatal\b)", line)
                        if res :
                            result["mortality"] = "yes"

    if result['species'] != [] :
        result['species'] = speciesParsing(result['species'], text, lang) # to associate a scientific name with a vernacular name
        result['country'], admin, latLng  = adminParsing(result['country'], headerCountries, text)
        result['admin1'] = admin[0]
        result['admin2'] = admin[1]
        result['admin3'] = admin[2]
        result['admin4'] = admin[3]
        result['admin5'] = admin[4]
        # production du JSON
        print(admin, latLng)
        event = {'archive_number': promed_archive_number,
                 'publication_date': promed_archive_number.split(".")[0],
                'url': promed_url,
                'subject': subject,
                'subpost' : result['subpost'],
                'subpost_header' : subpost_header,
                'event_date': result["event_date"],
                'serotypes': result['serotype'],
                'mortality': result['mortality'],
                'species': result['species'],
                'countries': [],
                'places': [],
                'GAUL': 0,
                'text': text 
                }
        # TO DO :
        # If a place in an admin doesn't contain a place already mentioned, it must be added
        nbPlaces = 0
        for numAdmin in range(4, -1, -1) :
            if len(admin[numAdmin]) > 0 :
                event["GAUL"] = numAdmin+1
                numL = 0
                for name in admin[numAdmin] :
                    country = latLng[numAdmin][numL][2]
                    event['places'].append({'name':name, 'lat':latLng[numAdmin][numL][0], 'lon':latLng[numAdmin][numL][1], 'country':country})
                    if country not in event['countries'] : event['countries'].append(country)
                    numL =+ 1
                    nbPlaces += 1
                break
        if nbPlaces == 0 :
            for name in headerCountries :
                lat = ''
                lng = ''
                if name in countries :
                    lat = countries[name][0]
                    lng = countries[name][1]
                event['countries'].append({'name':name, 'lat':lat, 'lon':lng})
        eventsJson.append(event)
        print(event)
        result['admin1'] = ','.join(result['admin1'])
        result['admin2'] = ','.join(result['admin2'])
        result['admin3'] = ','.join(result['admin3'])
        result['admin4'] = ','.join(result['admin4'])
        result['admin5'] = ','.join(result['admin5'])
    lastResult = copy.deepcopy(result)
    return lastResult

def bodyParsing(result, headerSerotypes, headerSpecies, headerCountries, post_text, lang, subject, promed_archive_number, promed_url) :
    """
    Affected animals:
    In this post:
    [1] UK (England): grey seal, harbor seal, red fox, HPAI H5N8
    [2] Croatia (Vukovarso-Srijemska): mute swan, HPAI H5N8
    ...
    [1]
    """
    """ TRACE
    FR = open("text1.txt", "w")
    FR.write(post_text)
    FR.close()
    """
    post_text = re.sub(r'\[\D+\]', '', post_text)  # [edited]
    # test of a composite post
    headerList = re.findall(r'\[(\d{1,3})\]\s*([^[]+)', post_text, flags=re.DOTALL)
    if re.search(r'\[1\].+\[2\]', post_text, flags=re.DOTALL) :
        print("COMPOSITE POST")
        #print(headerList)  
        headerDict = {}
        for header in headerList :
            subpost_text = re.sub(r'(.+)[Cc]ommunicated by.+', r'\1', header[1], flags=re.DOTALL)
            headerDict[header[0]] = subpost_text
        results = []
        for headerNum in headerDict :
            #print(headerNum, headerDict[headerNum])
            # TRACE
            #FR = open("subpost"+str(headerNum)+".txt", "w")
            #FR.write(headerDict[headerNum])
            #FR.close()
            
            print('-------------------------------------------------------------------------')
            # Extraction of each sub post
            result['region'] = ''
            result['country'] = ''
            result['admin1'] = ''; result['admin2'] = ''; result['admin3'] = ''; result['admin4'] = ''; result['admin5'] = ''
            result['species'] = []
            result['subpost'] = headerNum
            for criteria in directedResearch : result[criteria] = ''
            lastResult = bodyParsingByPost(result, headerSerotypes, headerSpecies, headerCountries, headerDict[headerNum], True, lang, subject, promed_archive_number, promed_url)
            # if lastResult['country'] == [] and headerCountries != [] : lastResult['country'] = headerCountries
            results.append(lastResult)
        return results
    else :
        post_text = re.sub(r'(.+)[Cc]ommunicated by.+', r'\1', post_text, flags=re.DOTALL)
        return [bodyParsingByPost(result, [], [], [], post_text, False, lang, subject, promed_archive_number, promed_url)]

def timeIntervalsGenerator(startDate, endDate) :
    # For generate a request month after month
    # TODO february 29
    nbDays = ['','31','28','31','30','31','30','31','31','30','31','30','31']
    timeIntervals = []
    date1 = startDate.split('/')
    date2 = endDate.split('/')
    if date1[2] > date2[2] :
        print("Inconsistent years !")
        return []
    if date1[2] == date2[2] :
        if date1[0] > date2[0] :
            print("Inconsistent months !")
            return []
        else :
            if date1[0] == date2[0] :
                if date1[1] > date2[1] :
                    print("Inconsistent days !")
                    return []
                else :
                    timeIntervals.append([startDate, endDate])
            else :
                for month in range(int(date1[0]), int(date2[0])+1) :
                    if month == int(date1[0]) : timeIntervals.append([startDate, date1[0]+'/'+str(nbDays[int(date1[0])])+'/'+date1[2]])
                    elif month == int(date2[0]) : timeIntervals.append([date2[0]+'/01/'+date1[2], endDate])
                    else :
                        smonth = str(month)
                        if month < 10 : smonth = '0'+str(month)
                        timeIntervals.append([smonth+'/01/'+date1[2], smonth+'/'+nbDays[month]+'/'+date1[2]])
    else :
        for year in range(int(date1[2]), int(date2[2])+1) :
            if year == int(date1[2]) :
                for month in range(int(date1[0]), 13) :
                    smonth = str(month)
                    if month < 10 : smonth = '0'+str(month)
                    if month == date1[0] : timeIntervals.append([startDate, date1[0]+'/'+nbDays[int(date1[0])]+'/'+date1[2]])
                    else : timeIntervals.append([smonth+'/01/'+date1[2], smonth+'/'+nbDays[month]+'/'+date1[2]])
            elif year == int(date2[2]) :
                for month in range(1, int(date2[0])+1) :
                    smonth = str(month)
                    if month < 10 : smonth = '0'+str(month)
                    if month == int(date2[0]) :
                        timeIntervals.append([smonth+'/01/'+str(year), endDate])
                    else : timeIntervals.append([smonth+'/01/'+str(year), smonth+'/'+nbDays[month]+'/'+str(year)])
            else :
                for month in range(1, 13) :
                    smonth = str(month)
                    if month < 10 : smonth = '0'+str(month)
                    timeIntervals.append([smonth+'/01/'+str(year), smonth+'/'+nbDays[month]+'/'+str(year)])
    return timeIntervals

def getCasesByDiseasesAndDates(diseases, startDate, endDate, inDepthAnalysis) :
    # into diseases : space character replaced by a plus => avian+influenza
    # date : jj/mm/aaaa

    # iteration over each month to avoid the limitation tp 50 results
    headers = {
        'user-agent': 'Mozilla/5.0',
        'Host':'promedmail.org',
        'Origin':'https://promedmail.org',
        'Referer':'https://promedmail.org/promed-posts',
        'Content-Type':'application/x-www-form-urlencoded;'}
    data = {
        'action': 'get_promed_search_content',
        'query[0][name]': 'kwby1',
        'query[0][value]': 'summary',
        'query[1][name]': 'search',
        'query[2][name]': 'date1',
        'query[3][name]': 'date2',
        'query[4][name]': 'feed_id',
        'query[4][value]':"1",
        'tz': "Europe/Paris"
    }
    #'query[2][value]': startDate,
    #'query[3][value]': endDate,
    driver = ''
    if inDepthAnalysis : driver = webdriver.Firefox()
    timeIntervals = timeIntervalsGenerator(startDate, endDate)
    values = []
    frp = open("positivePostsList.txt", "w")
    frn = open("negativePostsList.txt", "w")
    for interval in timeIntervals :
        for disease in diseases :
            data['query[1][value]'] = disease
            data['query[2][value]'] = interval[0]
            data['query[3][value]'] = interval[1]
            print("Request with", disease,"from",interval[0],"to",interval[1])
            try :
                r = requests.post('https://promedmail.org/wp-admin/admin-ajax.php', headers=headers, data=data).json()
            except :
                print("***** JSON NOT PARSABLE *****  ")
                pass
            else :
                print(r['res_count'], "responses")
                if int(r['res_count'] > 50) : print('************* WARNING *************',interval[0],"to",interval[1], ':', r['res_count'])
                cases = r['results'].split("\n")
                for case in cases :
                    match = re.search('<ul><li>\s*(.+)\s+<a .+?id="id(\d+?)"\s*class="slink">(.+?)\s*<', case)
                    if match :
                        report_date = match.group(1)
                        promed_id  = match.group(2)
                        infos = match.group(3)
                        archive_number = normalizedDate(report_date)+'.'+promed_id
                        link = "https://promedmail.org/promed-post/?id="+archive_number
                        result = {v:'' for v in criterias}
                        result['source'] = 'Promed'
                        result['disease'] = 'Avian influenza'
                        result['promed_id'] = promed_id
                        result['promed_archive_number'] = archive_number
                        result["link"] = link
                        result['species'] = []
                        lang = 'EN'  # Possibly modify in subjectParsing()
                        if inDepthAnalysis :
                            ### FULL ANALYSIS
                            results = []
                            header,body = getPostById(link, driver)
                            if header != '' : result, lang, subject = headerParsing(result, header)
                            if body != '' : results = bodyParsing(result, result['serotype'], result['species'], result['country'], body, lang, subject, archive_number, link)
                            else : results = [result]
                            for result in results :
                                if result['species'] != [] :
                                    result['species'] = ','.join(result['species'])
                                    result['region'] = ','.join(result['region'])
                                    result['country'] = ','.join(result['country'])
                                    values.append(result)
                                    frp.write(archive_number+':'+report_date+' '+infos+' >>> '+result['species']+'\n')
                                    print(json);
                                else :
                                    message = ''
                                    if header == '' and body == '' : message = ' *** no serveur response ***'
                                    frn.write(archive_number+':'+report_date+' '+infos+''+message+'\n')
                        else :
                            # HEADINGS ANALYSIS
                            result, lang = subjectParsing(result, infos, [], [])
                            if result['species'] != [] :
                                result['specie'] = ','.join(result['species'])
                                result['region'] = ','.join(result['region'])
                                result['country'] = ','.join(result['country'])
                                values.append(result)
                                frp.write(report_date+' '+infos+' >>> '+','.join(result['species'])+'\n')
                            else :
                                frn.write(report_date+' '+infos+'\n')
    frp.close()
    frn.close()
    if inDepthAnalysis : driver.close()
    return values

def getPostById(promed_url, driver) :
    print("getPostById('"+promed_url+"')")
    driver.get(promed_url)
    time.sleep(6)
    header = ''
    body = ''
    try : header = driver.find_element(By.CLASS_NAME, "publish_date_html").text  # promed_post_detail")
    except : 
        try : header = driver.find_element(By.CLASS_NAME, "promed_post_detail").text
        except : pass
    try : body = driver.find_element(By.CLASS_NAME, "text1").text
    except : pass
    return header, body

def searchByDates(manualCall, datemin, datemax) :
    diseases = ["avian+influenza"]  #, "bird+flu"]
    values = []
    if manualCall :
        data = str(datetime.datetime.now()).split(' ')[0].split('-')
        today = data[1]+'/'+data[2]+'/'+data[0]
        startDate = input("Starting date (mm/dd/aaaa) <if 0: today, 1: 01/01/2023; 2: 01/01/2022; 3: 01/01/2021; 4: 01/01/2020; 5: 01/01/2019> ? ")
        if startDate == '0' : startDate = today
        if startDate == '1' : startDate = '01/01/2023'
        if startDate == '2' : startDate = '01/01/2022'
        if startDate == '3' : startDate = '01/01/2021'
        if startDate == '4' : startDate = '01/01/2020'
        if startDate == '5' : startDate = '01/01/2019' 
        endDate = input("Ending date (mm/dd/aaaa) <if 0 : "+today+"> ? ")
        if endDate == '0' : endDate = today
        if re.match("\d\d/\d\d/\d\d\d\d", startDate) and re.match("\d\d/\d\d/\d\d\d\d", endDate) :
            typeOfAnalysis = input("0: analysis on headings / 1: full analysis : ")
            inDepth = False
            fullAnalysis = ''
            if typeOfAnalysis == '1' :
                inDepth = True
                fullAnalysis = "fullAnalysis"
            values = getCasesByDiseasesAndDates(diseases, startDate, endDate, inDepth)
        else : print("Syntax error in dates")
    else :  # call with dates in parameters
        if re.match("\d\d/\d\d/\d\d\d\d", datemin) and re.match("\d\d/\d\d/\d\d\d\d", datemax) :
            print('Analyse paramétrée entre', datemin, 'et', datemax)
            values = getCasesByDiseasesAndDates(diseases, datemin, datemax, True)
        else : print("Syntax error in dates")
    if values != [] :
        df = pd.DataFrame(values, columns=criterias)
        CSVfileName = "promed "+disease+" "+startDate.replace('/','-')+" "+endDate.replace('/','-')+" "+fullAnalysis+".csv"
        df.to_csv(CSVfileName, sep=";", quoting=csv.QUOTE_NONNUMERIC)
        print(CSVfileName, "created")
        JSONfileName = "promed "+disease+" "+startDate.replace('/','-')+" "+endDate.replace('/','-')+" "+fullAnalysis+".json"  
        fr = open(JSONfileName, "w")
        json.dump(eventsJson, fr, indent=4)
        fr.close()
        print(JSONfileName, "created")
        print('Merging')
        try :
            fd = open(CSVfileName)
            fr = open('promed Influenza.csv', 'a')
            nbLines = 0
            for line in fd.readlines()[1:] :
                fr.write(line)
                nbLines += 1
            fd.close()
            fr.close()
            print(nbLines, 'added in promed Influenza.csv')
        except Exception as e :
            print('Error :', e)
        try :
            fd = open('promed Influenza.json')
            previousEvents = json.load(fd)
            fd.close()
            previousEvents.extend(eventsJson)
            fr = open('promed Influenza.json')
            json.dump(previousEvents, fr, indent=4)
            fr.close()
            print(eventsJson.length, 'added in promed Influenza.json')
        except Exception as e :
            print('Error :', e)

def searchById() :
    # raccoon dog (2022) : 20220413.8702568
    # poultry, wild bird, mammal (2022) : 20230405.8709342
    # infección de aves no comerciales y mamíferos silvestres (2023) : 20230217.8708444
    promed_date = ''
    promed_id = ''
    while True :
        archive_number = input("date.id <exit 0> : ")
        if archive_number == '0' : return
        if archive_number == '1' :
            promed_date = '20220805' 
            promed_id = '8704881'
            break
        if archive_number == '2' :
            promed_date = '20230510'
            promed_id = '8709973'
            break
        if archive_number == '3' :
            promed_date = '20230405'
            promed_id = '8709342'
            break
        if archive_number == '4' :
            promed_date = ''
            promed_id = ''
            break
        res = re.search("(\d{8})\.(\d+)", archive_number)
        if res :
            promed_date = res.group(1)
            promed_id = res.group(2)
            break
        print("Format incorrect !")
    promed_base_url = "https://promedmail.org/promed-post/?id="
    promed_archive_number = promed_date+'.'+promed_id
    promed_url = promed_base_url + promed_archive_number
    result = {v:'' for v in criterias}    
    result['source'] = 'Promed'
    result['disease'] = 'Influenza'
    result['promed_id'] = promed_id
    result['promed_archive_number'] = promed_archive_number
    result['link'] = promed_url
    result['species'] = []
    driver = webdriver.Firefox()
    header,body = getPostById(promed_url, driver)
    results = []
    values = [] # list of results (possibility of composite posts)
    lang = 'EN'  # Possibly modify in subjectParsing()
    if header != '' : result, lang, subject = headerParsing(result, header)
    if body != '' : results = bodyParsing(result, result['serotype'], result['species'], result['country'], body, lang, subject, promed_archive_number, promed_url)
    else : results = [result]
    frp = open("positivePostsList.txt", "w")
    frn = open("negativePostsList.txt", "w")
    for result in results :
        if result['species'] != [] :
            result['species'] = ','.join(result['species'])
            result['region'] = ','.join(result['region'])
            result['country'] = ','.join(result['country'])
            values.append(result)
            frp.write(promed_archive_number+': '+header+' >>> '+result['species']+'\n')
        else :
            message = ''
            if header == '' and body == '' : message = ' *** no server response ***'
            frn.write(promed_archive_number+': '+header+''+message+'\n')
    frp.close()
    frn.close()
    print('-------------------------------------------------------------------------')
    #print(values)
    df = pd.DataFrame(values, columns=criterias)
    fileName = "promed "+disease+" "+promed_archive_number+".csv"
    df.to_csv(fileName, sep=";", quoting=csv.QUOTE_NONNUMERIC)
    print(fileName, "created")
    fileName = "promed "+disease+" "+promed_archive_number+".json"
    fr = open(fileName, "w")
    fr.write(json.dumps(eventsJson, indent=4))
    fr.close()
    print(fileName, "created")
    driver.close()

species = speciesImportation()
geographicalEntityImportation()

if len(sys.argv) == 3 : # scraping... datemin datemax
    print("Appel paramétré")
    searchByDates(False, sys.argv[1], sys.argv[2])
else :
    while True :
        response = input("Search by id (1) or by dates (2) <to exit: 0> ? ")
        if response == '0' : exit(1)
        elif response == '1' : searchById()
        elif response == '2' : searchByDates(True, '', '')


