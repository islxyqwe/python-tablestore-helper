How to use tablestore_helper
============================
安装:
------------
将tablestore_helper.py拷贝到您的项目目录中。

使用:
----------

导入tablestore_helper
>import tablestore_helper as tsh

初始化OTSClient
>otsClient = tablestore.OTSClient(config['ots_end_point'], config['access_key_id'], config['access_key_secret'], config['ots_instance_name'])

定义模型
>model = {'table_name':table_name,'primary_key':[(primary_key_name,primary_key_type=0,1,2,3),...],'default':{primary_key_name:primary_default_values,...}}
或使用 tsh.PK_INT,tsh.PK_STR,tsh.PK_BIN,tsh.PK_INC 来对应 整数,字符串,二进制,自增项类型。

调用helper
1.插入数据
>tsh.helper(otsClient).model(model).put({key:value}) -> 消耗,插入的主键和值的字典（用于插入自增项后查看）

2.用主键索引定位某条
>tsh.helper(otsClient).model(model).index({primary_keys:value}) -> 消耗,结果字典,next_token

3.获得数据
>tsh.helper(otsClient).model(model).where(primary_key_1_name,value=primary_key_1_value).where(primary_key_2_name,min=minvalue,max=maxvalue).filter(tsh.col('attr_key_name')> 1).select(max_column_counts) -> iter -> [数据字典]
注意: 表格存储中的数据按照主键排序（优先级按主键顺序）,这个方法或得到在最小的主键组合和最大的主键组合（不包含）之间的所有数据。 然后（由表格存储服务器）对其应用过滤。
例子:
你的数据 (order by pk1,pk2,pk3)
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
你的代码:
>tsh.helper(otsClient).model(model).where('pk1',min=1,max=3).where('pk2',min=4,max=6).where('pk3',min=5,max=7).filter(tsh.col('at1') > 14).select()
结果:
|pk1    |pk2   |pk3   |at1  |
|-------|------|------|-----|
|2      |1     |9     |15   |
|2      |3     |1     |33   |
|3      |4     |123   |42   |
|3      |5     |5     |99   |
并不会返回空集，而是以上数据，因为 2,1,9(15) 排序上比 1,4,5 更大,  3,5,5(99) 排序上比 3,6,7 更小。
2,2,44(7) 由于filter被移除。 3,6,7(4) 排序上与 3,6,4 相等，因此不被包含于结果。

使用filter:
tsh.helper.filter(tsh.myCond) -> tsh.helper
tsh.col(column_name) > value -> tsh.myCond
tsh.myCond & tsh.myCond -> tsh.myCond
例子:
(tsh.col('at1') > 5) & (tsh.col('at1') < 10) & (tsh.col('at1') != 8) | (tsh.col('act2') > 1)

4.寻找一条数据
>tsh.helper(otsClient).model(model).where(primary_key_1_name,value=primary_key_1_value).filter(tsh.col('attr_key_name') == 1).find() -> 数据字典
基本就是 select(1) 的别名

5.删除数据
>tsh.helper(otsClient).model(model).delete({primary_keys:value}) -> 消耗，返回行

6.分页取数据
中间的where与filter省略
>tsh.helper(otsClient).model(model).where.filter.paginate(pagesize,order) -> 消耗,[数据字典],token用来调用下一页
然后用返回的token调用
>tsh.helper(otsClient).model(model).where.filter.paginate(pagesize,order,token) -> 消耗,[数据字典],token用来调用下一页
order项指明了顺序，可以取'asc'正序或者'desc'倒序。