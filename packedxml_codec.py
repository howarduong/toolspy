import io
import struct
import xml.etree.ElementTree as ET

def write_dictionary(f, dictionary):
    """
    f: 二进制写入流（如 io.BytesIO 或 open(..., 'wb')）
    dictionary: 字符串列表
    """
    for text in dictionary:
        f.write(text.encode('utf-8'))
        f.write(b'\x00')
    f.write(b'\x00')  # 结尾

def read_dictionary(f):
    """
    f: 二进制读取流（如 io.BytesIO 或 open(..., 'rb')）
    return: 字符串列表
    """
    dictionary = []
    while True:
        chars = []
        while True:
            b = f.read(1)
            if not b or b == b'\x00':
                break
            chars.append(b)
        if not chars:
            break
        dictionary.append(b''.join(chars).decode('utf-8'))
    return dictionary

def read_little_endian_short(f):
    return struct.unpack('<h', f.read(2))[0]

def read_little_endian_int(f):
    return struct.unpack('<i', f.read(4))[0]

def read_data_descriptor(f):
    val = read_little_endian_int(f)
    end = val & 0xFFFFFFF
    type_ = val >> 28
    return {'end': end, 'type': type_}

def read_element_descriptors(f, number):
    result = []
    for _ in range(number):
        name_index = read_little_endian_short(f)
        data_desc = read_data_descriptor(f)
        result.append({'name_index': name_index, 'data_desc': data_desc})
    return result

def read_string(f, length):
    return f.read(length).decode('utf-8', errors='replace')

def read_number(f, length):
    if length == 1:
        return str(struct.unpack('<b', f.read(1))[0])
    elif length == 2:
        return str(read_little_endian_short(f))
    elif length == 4:
        return str(read_little_endian_int(f))
    elif length == 8:
        return str(struct.unpack('<q', f.read(8))[0])
    return '0'

def read_floats(f, length):
    n = length // 4
    return [struct.unpack('<f', f.read(4))[0] for _ in range(n)]

def read_boolean(f, length):
    return f.read(1)[0] == 1

def read_data(f, dictionary, element, offset, data_desc):
    length = data_desc['end'] - offset
    t = data_desc['type']
    if t == 0:  # Element
        read_element(f, dictionary, element)
    elif t == 1:  # String
        element.text = read_string(f, length)
    elif t == 2:  # Integer
        element.text = read_number(f, length)
    elif t == 3:  # Float
        floats = read_floats(f, length)
        element.text = ' '.join(f'{x:.6f}' for x in floats)
    elif t == 4:  # Boolean
        element.text = 'true' if read_boolean(f, length) else 'false'
    elif t == 5:  # Base64
        element.text = f.read(length).hex()
    else:
        element.text = f.read(length).hex()
    return data_desc['end']

def read_element(f, dictionary, parent):
    children_number = read_little_endian_short(f)
    self_data_desc = read_data_descriptor(f)
    children = read_element_descriptors(f, children_number)
    offset = read_data(f, dictionary, parent, 0, self_data_desc)
    for child_desc in children:
        name = dictionary[child_desc['name_index']]
        child = ET.Element(name)
        offset = read_data(f, dictionary, child, offset, child_desc['data_desc'])
        parent.append(child)

def decode_packedxml(bin_data, root_name='root'):
    f = io.BytesIO(bin_data)
    header = read_little_endian_int(f)
    f.read(1)
    dictionary = []
    while True:
        chars = []
        while True:
            b = f.read(1)
            if not b or b == b'\x00':
                break
            chars.append(b)
        if not chars:
            break
        dictionary.append(b''.join(chars).decode('utf-8'))
    root = ET.Element(root_name)
    read_element(f, dictionary, root)
    return ET.tostring(root, encoding='utf-8').decode('utf-8') 