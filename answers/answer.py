import os
import sys
import copy
import time
import random
import pyspark
import all_states
import math
from statistics import mean
from pyspark.rdd import RDD
from pyspark.sql import Row
from pyspark.sql import DataFrame
from pyspark.sql import SparkSession
from pyspark.ml.fpm import FPGrowth
from pyspark.sql.functions import desc, size, max, abs
from pyspark.sql.functions import monotonically_increasing_id
from pyspark.sql.functions import lit
from pyspark.sql.functions import array_contains,array
from pyspark import SparkContext
sc = SparkContext()

states=all_states.all_states
all_plants=None
data_f=None
data_df=None
data_points_index=None
MAX_FLOAT_VALUE = sys.float_info.max
'''
INTRODUCTION

With this assignment you will get a practical hands-on of frequent 
itemsets and clustering algorithms in Spark. Before starting, you may 
want to review the following definitions and algorithms:
* Frequent itemsets: Market-basket model, association rules, confidence, interest.
* Clustering: kmeans clustering algorithm and its Spark implementation.

DATASET

We will use the dataset at 
https://archive.ics.uci.edu/ml/datasets/Plants, extracted from the USDA 
plant dataset. This dataset lists the plants found in US and Canadian 
states.

The dataset is available in data/plants.data, in CSV format. Every line 
in this file contains a tuple where the first element is the name of a 
plant, and the remaining elements are the states in which the plant is 
found. State abbreviations are in data/stateabbr.txt for your 
information.
'''

'''
HELPER FUNCTIONS

These functions are here to help you. Instructions will tell you when
you should use them. Don't modify them!
'''

def init_spark():
    spark = SparkSession \
        .builder \
        .appName("Python Spark SQL basic example") \
        .config("spark.some.config.option", "some-value") \
        .getOrCreate()
    return spark

def toCSVLineRDD(rdd):
    a = rdd.map(lambda row: ",".join([str(elt) for elt in row]))\
           .reduce(lambda x,y: os.linesep.join([x,y]))
    return a + os.linesep

def toCSVLine(data):
    if isinstance(data, RDD):
        if data.count() > 0:
            return toCSVLineRDD(data)
        else:
            return ""
    elif isinstance(data, DataFrame):
        if data.count() > 0:
            return toCSVLineRDD(data.rdd)
        else:
            return ""
    return None


'''
PART 1: FREQUENT ITEMSETS

Here we will seek to identify association rules between states to 
associate them based on the plants that they contain. For instance, 
"[A, B] => C" will mean that "plants found in states A and B are likely 
to be found in state C". We adopt a market-basket model where the 
baskets are the plants and the items are the states. This example 
intentionally uses the market-basket model outside of its traditional 
scope to show how frequent itemset mining can be used in a variety of 
contexts.
'''

def data_frame(filename, n):
    '''
    Write a function that returns a CSV string representing the first 
    <n> rows of a DataFrame with the following columns,
    ordered by increasing values of <id>:
    1. <id>: the id of the basket in the data file, i.e., its line number - 1 (ids start at 0).
    2. <plant>: the name of the plant associated to basket.
    3. <items>: the items (states) in the basket, ordered as in the data file.

    Return value: a CSV string. Using function toCSVLine on the right 
                  DataFrame should return the correct answer.
    Test file: tests/test_data_frame.py
    '''
    spark = init_spark()
    lines = spark.read.text(filename).rdd
    parts= lines.map(lambda row: row.value.split(","))
    rdd_data = parts.map(lambda p: Row(name=p[0], place=p[1:]))
    df = spark.createDataFrame(rdd_data)
    df_indexed = df.select("*").withColumn("id", monotonically_increasing_id())
    df_final = df_indexed.select("id","name","place")
    op = toCSVLine(df_final.limit(n))
    return op

def frequent_itemsets(filename, n, s, c):
    '''
    Using the FP-Growth algorithm from the ML library (see 
    http://spark.apache.org/docs/latest/ml-frequent-pattern-mining.html), 
    write a function that returns the first <n> frequent itemsets 
    obtained using min support <s> and min confidence <c> (parameters 
    of the FP-Growth model), sorted by (1) descending itemset size, and 
    (2) descending frequency. The FP-Growth model should be applied to 
    the DataFrame computed in the previous task. 
    
    Return value: a CSV string. As before, using toCSVLine may help.
    Test: tests/test_frequent_items.py
    '''
    spark = init_spark()
    lines = spark.read.text(filename).rdd
    parts= lines.map(lambda row: row.value.split(","))
    rdd_data = parts.map(lambda p: Row(name=p[0], items=p[1:]))
    df = spark.createDataFrame(rdd_data)
    fpGrowth = FPGrowth(itemsCol="items", minSupport=s, minConfidence=c)
    model = fpGrowth.fit(df)
    model_1 = model.freqItemsets.orderBy([size("items"),"freq"],ascending=[0,0])
    final_op = toCSVLine(model_1.limit(n))
    return final_op
    '''return "not implemented"'''

def association_rules(filename, n, s, c):
    '''
    Using the same FP-Growth algorithm, write a script that returns the 
    first <n> association rules obtained using min support <s> and min 
    confidence <c> (parameters of the FP-Growth model), sorted by (1) 
    descending antecedent size in association rule, and (2) descending 
    confidence.

    Return value: a CSV string.
    Test: tests/test_association_rules.py
    '''
    spark = init_spark()
    lines = spark.read.text(filename).rdd
    parts= lines.map(lambda row: row.value.split(","))
    rdd_data = parts.map(lambda p: Row(name=p[0], items=p[1:]))
    df = spark.createDataFrame(rdd_data)
    fpGrowth = FPGrowth(itemsCol="items", minSupport=s, minConfidence=c)
    model = fpGrowth.fit(df)
    model_1 = model.associationRules.orderBy([size("antecedent"),"confidence"],ascending=[0,0])
    model_2 = model_1.drop("lift")
    final_op = toCSVLine(model_2.limit(n))
    return final_op

def interests(filename, n, s, c):
    '''
    Using the same FP-Growth algorithm, write a script that computes 
    the interest of association rules (interest = |confidence - 
    frequency(consequent)|; note the absolute value)  obtained using 
    min support <s> and min confidence <c> (parameters of the FP-Growth 
    model), and prints the first <n> rules sorted by (1) descending 
    antecedent size in association rule, and (2) descending interest.

    Return value: a CSV string.
    Test: tests/test_interests.py
    '''
    spark = init_spark()
    lines = spark.read.text(filename).rdd
    parts= lines.map(lambda row: row.value.split(","))
    rdd_data = parts.map(lambda p: Row(name=p[0], items=p[1:]))
    df = spark.createDataFrame(rdd_data)
    total_count = df.count()
    fpGrowth = FPGrowth(itemsCol="items", minSupport=s, minConfidence=c)
    model = fpGrowth.fit(df)
    model_updated = model.associationRules.join(model.freqItemsets,model.associationRules['consequent']==model.freqItemsets['items'])
    model_with_interest = model_updated.withColumn("interest",lit(calculate_interest(model_updated.confidence,model_updated.freq,total_count)))
    model_1 = model_with_interest.drop("lift")
    model_2 = model_1.orderBy([size("antecedent"),"interest"],ascending=[0,0])
    final_op = toCSVLine(model_2.limit(n))
    return final_op


def calculate_interest(confidence,frequency,total_count):
    interest = abs(confidence - (frequency/total_count))
    return interest
'''
PART 2: CLUSTERING

We will now cluster the states based on the plants that they contain.
We will reimplemented and use the kmeans algorithm. States will be 
represented by a vector of binary components (0/1) of dimension D, 
where D is the number of plants in the data file. Coordinate i in a 
state vector will be 1 if and only if the ith plant in the dataset was 
found in the state (plants are ordered alphabetically, as in the 
dataset). For simplicity, we will initialize the kmeans algorithm 
randomly.

An example of clustering result can be visualized in states.png in this 
repository. This image was obtained with R's 'maps' package (Canadian 
provinces, Alaska and Hawaii couldn't be represented and a different 
seed than used in the tests was used). The classes seem to make sense 
from a geographical point of view!
'''

def data_preparation(filename, plant, state):
    '''
    This function creates an RDD in which every element is a tuple with 
    the state as first element and a dictionary representing a vector 
    of plant as a second element:
    (name of the state, {dictionary})

    The dictionary should contains the plant names as a key. The 
    corresponding value should be 1 if the plant occurs in the state of 
    the tuple and 0 otherwise.

    You are strongly encouraged to use the RDD created here in the 
    remainder of the assignment.

    Return value: True if the plant occurs in the state and False otherwise.
    Test: tests/test_data_preparation.py
    '''
    spark = init_spark()
    lines = spark.read.text(filename).rdd
    parts= lines.map(lambda row: row.value.split(","))
    rdd_data = parts.map(lambda p: Row(plant_name=p[0], states=p[1:]))
    global data_df
    data_df = spark.createDataFrame(rdd_data)
    data_df.cache()
    all_plants = data_df.select(data_df.plant_name).rdd.flatMap(lambda x: x).collect()
    rdd=createDict(data_df,all_plants)
    global data_f
    data_f = spark.createDataFrame(rdd)
    data_f.cache()
    dict_op=getFromDict(state)
    row = Row(**dict_op[0][0])
    if  plant in row.asDict().keys() and row.asDict()[plant]==1:
        return True
    else:
        return False

def getFromDict(state):
    dict_op = data_f.select(data_f._2).where(data_f._1==state).collect()
    return dict_op

def createDict(df,all_plants):
    dict_list=[()]
    for state in states:
        plant_names = df.select(df.plant_name).where(array_contains(df.states,state)).rdd.flatMap(lambda x: x).collect()
        dict1= dict( [ (plant_name,1) if plant_name in plant_names  else (plant_name,0) for plant_name in all_plants] )
        tuple_data=(state,dict1)
        dict_list.append(tuple_data)
    rdd = sc.parallelize(dict_list[1:])
    return rdd

def distance2(filename, state1, state2):
    '''
    This function computes the squared Euclidean
    distance between two states.
    
    Return value: an integer.
    Test: tests/test_distance.py
    '''
    tuple_list1 = [()]
    tuple_list2 = [()]
    dict_op1=getFromDict(state1)
    dict_op2=getFromDict(state2)
    list1=list(dict_op1[0][0].values())
    list2=list(dict_op2[0][0].values())
    points = zip(list1, list2)
    diffs_squared_distance = [pow(a - b, 2) for (a, b) in points]
    return sum(diffs_squared_distance)

def init_centroids(k, seed):
    '''
    This function randomly picks <k> states from the array in answers/all_states.py (you
    may import or copy this array to your code) using the random seed passed as
    argument and Python's 'random.sample' function.

    In the remainder, the centroids of the kmeans algorithm must be
    initialized using the method implemented here, perhaps using a line
    such as: `centroids = rdd.filter(lambda x: x['name'] in
    init_states).collect()`, where 'rdd' is the RDD created in the data
    preparation task.

    Note that if your array of states has all the states, but not in the same
    order as the array in 'answers/all_states.py' you may fail the test case or
    have issues in the next questions.

    Return value: a list of <k> states.
    Test: tests/test_init_centroids.py
    '''
    random.seed(seed)
    random_states = random.sample(all_states.all_states,k)
    return random_states

def first_iter(filename, k, seed):
    '''
    This function assigns each state to its 'closest' class, where 'closest'
    means 'the class with the centroid closest to the tested state
    according to the distance defined in the distance function task'. Centroids
    must be initialized as in the previous task.

    Return value: a dictionary with <k> entries:
    - The key is a centroid.
    - The value is a list of states that are the closest to the centroid. The list should be alphabetically sorted.

    Test: tests/test_first_iter.py
    '''
    global data_points_index
    states_fi=sorted(states)
    random.seed(seed)
    centers =random.sample(states,k)
    data_points_index = list(states_fi)
    v = assign_states(centers)
    return v            
    

def assign_states(centers):
    iter_dict={}
    for iteration in range(1):
        for data_point_index in data_points_index:
            min_value = float('inf')
            min_goal = None
            min_data_point = None
            data_point_center_distance=[]
            for center in centers:
                calculated_distance = distance2("name",data_point_index,center)
                data_point_center_distance.append(calculated_distance)
                index=data_point_center_distance.index(min(data_point_center_distance))
            iter_dict[data_point_index]=centers[index]
    
    v = {}

    for key, value in sorted(iter_dict.items()):
        v.setdefault(value, []).append(key)
    return v

def kmeans(filename, k, seed):
    '''
    This function:
    1. Initializes <k> centroids.
    2. Assigns states to these centroids as in the previous task.
    3. Updates the centroids based on the assignments in 2.
    4. Goes to step 2 if the assignments have not changed since the previous iteration.
    5. Returns the <k> classes.

    Note: You should use the list of states provided in all_states.py to ensure that the same initialization is made.
    
    Return value: a list of lists where each sub-list contains all states (alphabetically sorted) of one class.
                  Example: [["qc", "on"], ["az", "ca"]] has two 
                   classes: the first one contains the states "qc" and 
                  "on", and the second one contains the states "az" 
                  and "ca".
    Test file: tests/test_kmeans.py
    '''
    '''spark = init_spark()
    states_fi=sorted(states)
    random.seed(seed)
    centroids =random.sample(states,k)
    first_iter_centroids=assign_states(centroids)
    print(first_iter_centroids)
    while True:
    old_clusters = assign_states(centroids)
    print(old_clusters)
    new_clusters = recalculate_cluster_centroids(old_clusters)
    print(new_clusters.collectAsMap())
    new_cluster_keys = new_clusters.keys().collect()
    if(new_clusters==None):
        return []
    if first_iter_centroids.keys().collect() == new_clusters.keys().collect():
        return best_clusters
            
    print(new_clusters)'''
    return []

def recalculate_cluster_centroids(clusters):
    rdd_clusters=sc.parallelize(clusters)
    op=rdd_clusters.values().map(lambda points: (assign_states(points)))
    print(op)
    return op

'''def nearest_centroid(values,centers):
    iter_dict={}
    for iteration in range(1):
        for value in values:
            min_value = float('inf')
            min_goal = None
            min_data_point = None
            data_point_center_distance=[]
            for center in centers:
                calculated_distance = distance2("name",value,center)
                data_point_center_distance.append(calculated_distance)
                index=data_point_center_distance.index(min(data_point_center_distance))
            iter_dict[value]=centers[index]
    
    v = {}

    for key, value in sorted(iter_dict.items()):
        v.setdefault(value, []).append(key)
    return v,value'''
