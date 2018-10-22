# -*- coding: utf-8 -*-
import tablestore
import pickle
import gzip
PK_INT = 0
PK_STR = 1
PK_BIN = 2
PK_INC = 3


def toTSRow(struct, data):
    def getPK(k, v):
        if k in data:
            if v in (0,3):
                return int(data[k])
            return data[k]
        else:
            if v == PK_INC:
                return tablestore.PK_AUTO_INCR
            else:
                if k in struct['default']:
                    return struct['default'][k]
                else:
                    raise('PK %s except' % k)
    pks = {k for k, v in struct['primary_key']}
    pk = [(k, getPK(k, v)) for k, v in struct['primary_key']]
    ac = [(k, v) for k, v in data.items() if not k in pks]
    return tablestore.Row(pk, ac)


def toPyDict(struct, row):
    if row is None:
        return None
    return dict({k: v for k, v in row.primary_key}, **{k: v for k, v, s in row.attribute_columns})


class helper:
    def __init__(self, client):
        self.__client = client
        self.__PKCond = {}
        self.__field = []
        self.cond = None

    def model(self, model):
        self.__model = model
        return self

    def put(self, data):
        c,rt =  self.__client.put_row(self.__model['table_name'], toTSRow(self.__model, data), tablestore.Condition('IGNORE'), return_type=tablestore.ReturnType.RT_PK)
        return c,toPyDict(self.__model,rt)

    def field(self, fields):
        self.__field = fields
        return self

    def index(self, data):
        pk = toTSRow(self.__model, data).primary_key
        c,rt,nt = self.__client.get_row(self.__model['table_name'], pk, self.__field, self.cond)
        return c,toPyDict(self.__model,rt),nt

    def filter(self, cond):
        if type(cond) is myCond:
            self.cond = cond.cond
        else:
            return NotImplemented

    def where(self, PKname, **kwargs):
        PKmin = tablestore.INF_MIN
        PKmax = tablestore.INF_MAX
        v = {k:v for k,v in self.__model['primary_key']}[PKname]
        toint = v in (0,3)
        for k, v in kwargs.items():
            if toint:
                v = int(v)
            if k == 'value':
                self.__PKCond[PKname] = (v, v)
                return self
            elif k == 'min':
                PKmin = v
            elif k == 'max':
                PKmax = v
            else:
                return NotImplemented
        
        self.__PKCond[PKname] = (PKmin, PKmax)
        return self

    def select(self,count = None):
        consumed_counter = tablestore.CapacityUnit(0, 0)
        pks = [(k,self.__PKCond[k][0] if k in self.__PKCond else tablestore.INF_MIN) for k,
               _ in self.__model['primary_key']]
        pke = [(k,self.__PKCond[k][1] if k in self.__PKCond else tablestore.INF_MAX) for k,
               _ in self.__model['primary_key']]
        for row in self.__client.xget_range(self.__model['table_name'], tablestore.Direction.FORWARD, pks, pke, consumed_counter, self.__field,count, column_filter=self.cond):
            yield toPyDict(self.__model, row)

    def find(self):
        tmp = list(self.select(1))
        if len(tmp) == 0:
            return None
        return tmp[0]

    def delete(self, data):
        row = toTSRow(self.__model, data)
        newrow = tablestore.Row(row.primary_key)
        return self.__client.delete_row(self.__model['table_name'], newrow, tablestore.Condition('IGNORE'))
    
    def paginate(self,pages,order,pagestart=None):
        consumed_counter = tablestore.CapacityUnit(0, 0)
        consumed_counter.read = 0
        consumed_counter.write = 0
        pks = [(k,self.__PKCond[k][0] if k in self.__PKCond else tablestore.INF_MIN) for k,
               _ in self.__model['primary_key']]
        pke = [(k,self.__PKCond[k][1] if k in self.__PKCond else tablestore.INF_MAX) for k,
               _ in self.__model['primary_key']]
        if order=='asc':
            order = tablestore.Direction.FORWARD
        elif order=='desc':
            order = tablestore.Direction.BACKWARD
            pks,pke = pke,pks
        else:
            raise(Exception('unsupport order' + order))
        if not pagestart is None:
            pagestart = pickle.loads(pagestart)
            if pagestart is None:
                return consumed_counter,[],pickle.dumps(None,0)
            pks=pagestart
        res = []
        while pks:
            c,pks,rows,_ = self.__client.get_range(self.__model['table_name'],order,pks,pke,self.__field,pages,column_filter=self.cond)
            consumed_counter.read += c.read
            for r in rows:
                res.append(toPyDict(self.__model,r))
                pages-=1
                if pages<=0:
                    return consumed_counter,res,pickle.dumps(pks,0)
        return consumed_counter,res,pickle.dumps(pks,0)


class col:
    def __init__(self, name):
        self.name = name

    def __lt__(self, data):
        return myCond(tablestore.SingleColumnCondition(self.name, data, tablestore.ComparatorType.LESS_THAN))

    def __gt__(self, data):
        return myCond(tablestore.SingleColumnCondition(self.name, data, tablestore.ComparatorType.GREATER_THAN))

    def __ge__(self, data):
        return myCond(tablestore.SingleColumnCondition(self.name, data, tablestore.ComparatorType.GREATER_EQUAL))

    def __le__(self, data):
        return myCond(tablestore.SingleColumnCondition(self.name, data, tablestore.ComparatorType.LESS_EQUAL))

    def __eq__(self, data):
        return myCond(tablestore.SingleColumnCondition(self.name, data, tablestore.ComparatorType.EQUAL))

    def __ne__(self, data):
        return myCond(tablestore.SingleColumnCondition(self.name, data, tablestore.ComparatorType.NOT_EQUAL))


class myCond:
    def __init__(self, cond):
        self.cond = cond

    def __and__(self, other):
        if type(other) is myCond:
            cCond = tablestore.CompositeColumnCondition(
                tablestore.LogicalOperator.AND)
            cCond.add_sub_condition(self.cond)
            cCond.add_sub_condition(other.cond)
            return myCond(cCond)
        else:
            return NotImplemented

    def __or__(self, other):
        if type(other) is myCond:
            cCond = tablestore.CompositeColumnCondition(
                tablestore.LogicalOperator.OR)
            cCond.add_sub_condition(self.cond)
            cCond.add_sub_condition(other.cond)
            return myCond(cCond)
        else:
            return NotImplemented

    def __invert__(self):
        cCond = tablestore.CompositeColumnCondition(
            tablestore.LogicalOperator.NOT)
        cCond.add_sub_condition(self.cond)
        return myCond(cCond)
