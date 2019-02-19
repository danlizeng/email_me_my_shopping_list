import sqlite3
import random
from itertools import chain
import pandas as pd


dish_cnt = [2, 2, 2, 2, 0, 2, 0]  # From Mon-Sun how many non-soup dishes do you want per day?
soup_cnt = [0, 0, 0, 0, 0, 1, 0]  # From Mon-Sun how many soup do you want per day?
flavors_to_exclude = [3]          # 1.红烧; 2.卤煮; 3.酸甜; 4.酸辣; 5.鲜辣; 6.清淡;
                                  # 7.咸鲜; 8.甜鲜; 9.淡鲜; 10.麻辣


conn = sqlite3.connect('dishes.db')
print('Dishes database opened successfully!')
cur = conn.cursor()
dish_plan = {}
soup_plan = {}


# a function to get rid of the tuples WITH JUST ONE VALUE that SQLite selected
def de_tuples(ls):
    ls = list(map(lambda t: t[0], ls))
    return ls

def zip_dict(d1, d2):
    d3 = {}
    for i in set(d1.keys()).intersection(d2.keys()):
        d3[i] = d1[i] + d2[i]
    return d3


# get dish_ids pools for random sampling
if len(flavors_to_exclude) != 0:
    t = tuple(flavors_to_exclude)

    cur.execute(
        'SELECT dish_id FROM recipes WHERE category_id = 5 AND flavor_id NOT IN (?)', t)
    soup_id_pool = de_tuples(cur.fetchall())
    cur.execute(
        'SELECT dish_id FROM recipes WHERE category_id = 3 AND flavor_id NOT IN (?)', t)
    veggie_id_pool = de_tuples(cur.fetchall())
    cur.execute(
        'SELECT dish_id FROM recipes WHERE category_id IN (2, 3) AND flavor_id NOT IN (?)', t)
    veggienmix_id_pool = de_tuples(cur.fetchall())
    cur.execute(
        'SELECT dish_id FROM recipes WHERE category_id NOT IN (3, 5) AND flavor_id NOT IN (?)', t)
    other_id_pool = de_tuples(cur.fetchall())
    cur.execute(
        'SELECT dish_id FROM recipes WHERE category_id = 2 AND flavor_id NOT IN (?)', t)
    mix_id_pool = de_tuples(cur.fetchall())

else:
    cur.execute('SELECT dish_id FROM recipes WHERE category_id = 5')
    soup_id_pool = de_tuples(cur.fetchall())
    cur.execute('SELECT dish_id FROM recipes WHERE category_id = 3')
    veggie_id_pool = de_tuples(cur.fetchall())
    cur.execute('SELECT dish_id FROM recipes WHERE category_id IN (2, 3)')
    veggienmix_id_pool = de_tuples(cur.fetchall())
    cur.execute('SELECT dish_id FROM recipes WHERE category_id NOT IN (3, 5)')
    other_id_pool = de_tuples(cur.fetchall())
    cur.execute('SELECT dish_id FROM recipes WHERE category_id = 2')
    mix_id_pool = de_tuples(cur.fetchall())

# query flavor_mapper, a dict of dish_id: flavor_id pairs
if len(flavors_to_exclude) != 0:
    t = tuple(flavors_to_exclude)
    cur.execute('SELECT dish_id, flavor_id FROM recipes where flavor_id NOT IN (?)', t)
    flavor_mapper = dict(cur.fetchall())
else:
    cur.execute('SELECT dish_id, flavor_id FROM recipes')
    flavor_mapper = dict(cur.fetchall())


def pick_the_soups():
    """
    每天最多一个汤 
    """
    print('先选汤。。。')
    existing_soup = []

    for i in list(range(7)):
        if soup_cnt[i] > 1:
            print('又不是水牛喝这么多汤干嘛？周%d喝一个够了。' % (i + 1))
            soup_cnt[i] = 1
            soup_plan[i] = random.sample(
                list(set(soup_id_pool) - set(existing_soup)), 1)
            existing_soup += soup_plan[i]
        elif soup_cnt[i] < 1:
            soup_cnt[i] = 0
            soup_plan[i] = []
        else:
            soup_plan[i] = random.sample(
                list(set(soup_id_pool) - set(existing_soup)), 1)
            existing_soup += soup_plan[i]
    return soup_plan


def pick_the_dishes():
    """
    为了保证人民的健康，每天都必须有一素菜或者花荤；
    如果某天只有一道菜，那必定是花荤；每天吃的菜不可是
    同一口味。
    """

    print('再来选菜，每天都要吃蔬菜！')
    existing_dishes = []

    for i in list(range(7)):
        if dish_cnt[i] > 9:
            dish_cnt[i] = 9
        pick(dish_cnt[i], existing_dishes, dish_plan, i)
    return dish_plan


def pick(num_of_dishes, existing_dishes, dish_plan, weekday):
    # 0 or negative means you don't want to cook that weekday
    if num_of_dishes < 1:
        print('周%d不想做饭就休息一下' % (weekday + 1))
        dish_plan[weekday] = []

    # if you want 1 dish for someday then you have to cook something w/
    # both meat & veggie so it's healthy :)
    # Yes I made the rule and you're not allowed to change this.
    elif num_of_dishes == 1:
        dish_plan[weekday] = random.sample(
            list(set(mix_id_pool) - set(existing_dishes)), 1)
        existing_dishes += dish_plan[weekday]

    # if you want 2 dishes for someday then you need at least 1 pure veggie
    # or meat+veggie dish, and I suppose you don't want 2 dishes with the
    # same flavor in one day.
    elif num_of_dishes == 2:
        d1 = random.sample(
            list(set(veggienmix_id_pool) - set(existing_dishes)), 1)
        existing_dishes += d1
        while True:
            d2 = random.sample(
                list(set(other_id_pool) - set(existing_dishes)), 1)
            if flavor_mapper[d1[0]] != flavor_mapper[d2[0]]:
                existing_dishes += d2
                dish_plan[weekday] = d1 + d2
                break

    else:
        d1 = random.sample(
            list(set(veggie_id_pool) - set(existing_dishes)), 1)
        existing_dishes += d1
        while True:
            d2 = random.sample(
                list(set(other_id_pool) - set(existing_dishes)), num_of_dishes - 1)
            flavor_ls = [flavor_mapper[d] for d in (d1 + d2)]
            if len(flavor_ls) == len(set(flavor_ls)):
                existing_dishes += d2
                dish_plan[weekday] = d1 + d2
                break


def process_meal_plan(selected_recipes, dish_plan, soup_plan):
    dish_mapper = {}

    for i in selected_recipes:
        dish_mapper[i[0]] = i[1]

    meal_plan = zip_dict(dish_plan, soup_plan)

    weekdays = {0:'Mon', 1:'Tue', 2:'Wed', 3:'Thu', 4:'Fri', 5:'Sat', 6:'Sun'}

    meal_plan = dict((weekdays[k],[dish_mapper[i] for i in v])
                     for k, v in meal_plan.items())
    print(meal_plan)
    return meal_plan


def print_results():
    '''
    this function runs the pick functions above which randomly sampled dish_ids
    according to multiple rules, then it queries the DB and generates readable 
    meal plan & shopping list, happy shopping n cooking!
    '''
    pick_the_soups()
    pick_the_dishes()

    #combine dish & soup plans, query the recipes and generate final meal plan
    dish_ls = list(chain.from_iterable(list(dish_plan.values())))
    soup_ls = list(chain.from_iterable(list(soup_plan.values())))
    t = tuple(dish_ls + soup_ls)
    query_recipes = \
        'SELECT * FROM recipes WHERE dish_id in (' + ', '.join('?' * len(t)) + ')'
    cur.execute(query_recipes, t)
    selected_recipes = cur.fetchall()
    process_meal_plan(selected_recipes, dish_plan, soup_plan)

    #query the ingredients you need for cooking next week and generates your
    #shopping list
    col_slice = [t[4:] for t in selected_recipes]
    ingredients = []
    ingredients_cnt = {}

    for i in range(len(col_slice)):
        ingredients += col_slice[i]

    for i in list(set(ingredients)):
        ingredients_cnt[i] = ingredients.count(i)

    t = tuple(set(ingredients))
    query_ingredients = \
        'SELECT * FROM ingredients WHERE ingredient_id in (' + ', '.join('?' * len(t)) + ')'
    cur.execute(query_ingredients, t)
    selected_ingredients = cur.fetchall()

    shopping_list = pd.DataFrame(selected_ingredients,
                                 columns=['ingredient_id', 'ingredient_name', 'section_id']
                                 )
    shopping_list['count'] = shopping_list['ingredient_id'].map(ingredients_cnt)
    shopping_list = shopping_list.sort_values(['section_id', 'count'])
    print(shopping_list[['ingredient_name', 'count']])


print_results()


cur.close()
conn.close()
print('Database connection closed successfully!')
