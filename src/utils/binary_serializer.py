import  pickle
class BinarySerializer:
    @staticmethod
    def serialize(obj):
        serialized_obj = pickle.dumps(obj)
        return  serialized_obj
    @staticmethod
    def deserialize(serialized_obj):
        obj = pickle.loads(serialized_obj)
        return  obj