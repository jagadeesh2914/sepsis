# -*- coding: utf-8 -*-
"""project-sepsis.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/github/AdarshShah/final-year-project/blob/master/project_sepsis.ipynb

#Import Libraries
"""

import time
import pandas as pd
import psycopg2
import getpass
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

"""# Declare Global Variables"""

user = 'postgres'
host = 'localhost'
dbname = 'mimic'
schema = 'mimiciii'
password = 'postgres'
icd9_code = '99592'
minMaxScaler = dict()
itemMeans = dict()

"""# Create Database Connection"""

conn = psycopg2.connect(user=user,password=password,dbname=dbname,host=host)
cur = conn.cursor()
cur.execute('SET search_path to {}'.format(schema))

"""# Load Patient data

> Data from admissions suffering from severe sepsis
"""

query = """SELECT DISTINCT * FROM mimiciii.admissions i 
INNER JOIN mimiciii.diagnoses_icd USING(hadm_id)
INNER JOIN mimiciii.d_icd_diagnoses USING(icd9_code)
WHERE icd9_code LIKE '99592';
"""
admissions = pd.read_sql_query(sql=query,con=conn)
admissions['sepsis'] = 1

query = """SELECT DISTINCT * FROM mimiciii.admissions i 
INNER JOIN mimiciii.diagnoses_icd USING(hadm_id)
INNER JOIN mimiciii.d_icd_diagnoses USING(icd9_code)
WHERE icd9_code NOT LIKE '99592' LIMIT 4000;
"""
temp = pd.read_sql_query(sql=query,con=conn)
temp['sepsis'] = 0

admissions = admissions.append(temp)

"""> List Items from d_labitems and d_items"""

#d_items = ['Platelets','C Reactive Protein (CRP)','pH (Art)','HCO3','TCO2 (cap)']
#d_labitems = ['Leukocytes','Urea Nitrogen','Creatinine','Glucose','Calcium, Total','Sodium','Potassium','Bilirubin','Albumin','Lactate','pCO2','pO2','Hemoglobin']

#Append itemid below !!!!
d_item_ce = ['0','828','3789','6256','791','3750','1525','220615','811','3744','3745','1529','226537','837','3803','1536','4948','3066','227444','3835','3837','812','3736']  
d_item_cv = ['0','30006','44711','44441']
d_item_mv = ['0','225170']
d_labitem = ['51486','51006','50912','50809','50931','51478','50813','50820']

def get_pandas(items, table):
  query = "SELECT DISTINCT * FROM mimiciii."+table+" WHERE itemid IN " + str(tuple(items))
  items = pd.read_sql_query(sql=query,con=conn)
  return items

d_item_ce = get_pandas(d_item_ce,"d_items")
d_item_cv = get_pandas(d_item_cv,"d_items")
d_item_mv = get_pandas(d_item_mv,"d_items")
d_labitem = get_pandas(d_labitem,"d_labitems")

"""# Fetch items from mimic-iii

> CHARTEVENTS
"""

query = "SELECT * FROM mimiciii.chartevents WHERE itemid IN " + str(tuple(d_item_ce['itemid'])) + " AND hadm_id IN " + str(tuple(admissions['hadm_id'])) + " ORDER BY hadm_id,charttime,itemid;"
chartevents = pd.read_sql_query(sql=query,con=conn)

itemids = chartevents['itemid'].drop_duplicates()
temp = chartevents.pivot(index='row_id',columns='itemid',values='valuenum')
temp.fillna(value=temp.mean(skipna=True),inplace=True)
temp.replace()
for item in itemids:
  arr = np.reshape(np.array(temp[item]),(-1,1))
  minMaxScaler[item] = MinMaxScaler().fit(arr)

temp = dict(temp.mean())
for key in temp.keys():
  itemMeans[key] = temp[key]

chartevents.describe()

"""> INPUTEVENTS_CV"""

query = "SELECT * FROM mimiciii.inputevents_cv WHERE itemid IN " + str(tuple(d_item_cv['itemid'])) + " AND hadm_id IN " + str(tuple(admissions['hadm_id'])) + " ORDER BY hadm_id,charttime,itemid;"
inputevents_cv = pd.read_sql_query(sql=query,con=conn)

itemids = inputevents_cv['itemid'].drop_duplicates()
temp = inputevents_cv.pivot(index='row_id',columns='itemid',values='amount')
temp.fillna(value=temp.mean(skipna=True),inplace=True)
for item in itemids:
  arr = np.reshape(np.array(temp[item]),(-1,1))
  minMaxScaler[item] = MinMaxScaler().fit(arr)

temp = dict(temp.mean())
for key in temp.keys():
  itemMeans[key] = temp[key]

inputevents_cv.describe()

"""> INPUTEVENTS_MV"""

query = "SELECT * FROM mimiciii.inputevents_mv WHERE itemid IN ('225170') AND hadm_id IN " + str(tuple(admissions['hadm_id'])) + " ORDER BY hadm_id,starttime,itemid;"
inputevents_mv = pd.read_sql_query(sql=query,con=conn)

itemids = inputevents_mv['itemid'].drop_duplicates()
temp = inputevents_mv.pivot(index='row_id',columns='itemid',values='amount')
temp.fillna(value=temp.mean(skipna=True),inplace=True)
for item in itemids:
  arr = np.reshape(np.array(temp[item]),(-1,1))
  minMaxScaler[item] = MinMaxScaler().fit(arr)

temp = dict(temp.mean())
for key in temp.keys():
  itemMeans[key] = temp[key]

inputevents_mv.describe()

"""> LABEVENTS"""

query = "SELECT * FROM mimiciii.labevents WHERE itemid IN " + str(tuple(d_labitem['itemid'])) + " AND hadm_id IN " + str(tuple(admissions['hadm_id'])) + " ORDER BY hadm_id,charttime,itemid;"
labevents = pd.read_sql_query(sql=query,con=conn)

itemids = labevents['itemid'].drop_duplicates()
temp = labevents.pivot(index='row_id',columns='itemid',values='valuenum')
temp.fillna(value=temp.mean(skipna=True),inplace=True)
for item in itemids:
  arr = np.reshape(np.array(temp[item]),(-1,1))
  minMaxScaler[item] = MinMaxScaler().fit(arr)

temp = dict(temp.mean())
for key in temp.keys():
  itemMeans[key] = temp[key]

labevents.describe()

"""# Generate Tensors"""

hadm_id = admissions['hadm_id']
hadm_id.describe()

sepsis_dataset = []
for hadm in hadm_id:
  data = pd.DataFrame(data=itemMeans,index={0})

  temp = chartevents[chartevents['hadm_id'] == hadm]
  temp = temp.pivot(index='row_id',columns='itemid',values='valuenum')
  data = data.append(temp,ignore_index=False)
  
  temp = inputevents_cv[inputevents_cv['hadm_id'] == hadm]
  temp = temp.pivot(index='row_id',columns='itemid',values='amount')
  data = data.append(temp,ignore_index=False)
  
  temp = inputevents_mv[inputevents_mv['hadm_id'] == hadm]
  temp = temp.pivot(index='row_id',columns='itemid',values='amount')
  data = data.append(temp,ignore_index=False)

  temp = labevents[labevents['hadm_id'] == hadm]
  temp = temp.pivot(index='row_id',columns='itemid',values='valuenum')
  data = data.append(temp,ignore_index=False)

  data.fillna(value=itemMeans,inplace=True)
  data['sepsis'] = int(admissions[admissions['hadm_id']==hadm]['sepsis'].all())
  for key in minMaxScaler.keys():
    arr = np.reshape(np.array(data[key]),(-1,1))
    data[key] = minMaxScaler[key].transform(arr)
  sepsis_dataset.insert(len(sepsis_dataset),data)

len(sepsis_dataset)