How to use tablestore_helper
============================
install:
------------
copy tablestore_helper.py to your project folder.

usage:
----------

import tablestore_helper
>import tablestore_helper as tsh

init the otsclient
>otsClient = tablestore.OTSClient(config['ots_end_point'], config['access_key_id'], config['access_key_secret'], config['ots_instance_name'])

define the model
>model = {'table_name':table_name,'primary_key':[(primary_key_name,primary_key_type=0,1,2,3),...],'default':{primary_key_name:primary_default_values,...}}
or use tsh.PK_INT,tsh.PK_STR,tsh.PK_BIN,tsh.PK_INC for integer,string,binary,increment type.

call the helper
1.insert data
>tsh.helper(otsClient).model(model).put({key:value}) -> cosume,inserted primary_key and values(useful when insert data have increment column)

2.get data using primary index
>tsh.helper(otsClient).model(model).index({primary_keys:value}) -> consume,result dict,next_token

3.get data list
>tsh.helper(otsClient).model(model).where(primary_key_1_name,value=primary_key_1_value).where(primary_key_2_name,min=minvalue,max=maxvalue).filter(tsh.col('attr_key_name')> 1).select(max_column_counts) -> iter -> [data_dicts]
Attention: data in tablestore is sorted by primary keys,this method gets all data between the min primary_keys_set and the max one(exclusive).and then apply the filter on it.
example:
Your data (order by pk1,pk2,pk3)
|pk1    |pk2   |pk3   |at1  |
|-------|------|------|-----|
|1      |1     |3     |11   |
|1      |2     |15    |25   |
|1      |3     |6     |43   |
|2      |1     |9     |15   |
|2      |2     |44    |7    |
|2      |3     |1     |33   |
|3      |4     |123   |42   |
|3      |5     |5     |99   |
|3      |6     |7     |4    |
Your code:
>tsh.helper(otsClient).model(model).where('pk1',min=1,max=3).where('pk2',min=4,max=6).where('pk3',min=5,max=7).filter(tsh.col('at1') > 14).select()
Result:
|pk1    |pk2   |pk3   |at1  |
|-------|------|------|-----|
|2      |1     |9     |15   |
|2      |3     |1     |33   |
|3      |4     |123   |42   |
|3      |5     |5     |99   |
Because 2,1,9(15) is bigger than 1,4,5, and 3,5,5(99) is lesser than 3,6,7.
2,2,44(7) is removed by the filter. 3,6,7(4) is equal to 3,6,4 , and is not included in the result.

filter usage:
tsh.helper.filter(tsh.myCond) -> tsh.helper
tsh.col(column_name) > value -> tsh.myCond
tsh.myCond & tsh.myCond -> tsh.myCond
example:
(tsh.col('at1') > 5) & (tsh.col('at1') < 10) & (tsh.col('at1') != 8) | (tsh.col('act2') > 1)

4.find one data
>tsh.helper(otsClient).model(model).where(primary_key_1_name,value=primary_key_1_value).filter(tsh.col('attr_key_name') == 1).find() -> data_dict
Almost a alias to select(1)

5.delete a data
>tsh.helper(otsClient).model(model).delete({primary_keys:value}) -> consume,return_row

6.paginate data lists
>tsh.helper(otsClient).model(model).where.filter.paginate(pagesize,order) -> consume,[data_dict],token
>tsh.helper(otsClient).model(model).where.filter.paginate(pagesize,order,token) -> consume,[data_dict],token
order can be 'asc' or 'desc'.