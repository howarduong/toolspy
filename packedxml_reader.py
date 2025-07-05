import struct
import io
import xml.etree.ElementTree as ET

class PackedXmlDataType:
    Element = 0
    String = 1
    Integer = 2
    Float = 3
    Boolean = 4
    Base64 = 5

class PackedXmlDataDescriptor:
    def __init__(self, encoded):
        self.end = encoded & 0xFFFFFFF  # bottom 28 bits
        self.type = (encoded >> 28)     # top 4 bits

class PackedXmlElementDescriptor(PackedXmlDataDescriptor):
    def __init__(self, name_index, name, encoded):
        super().__init__(encoded)
        self.name_index = name_index
        self.name = name

class PackedXmlReader:
    Packed_Header = 0x62A14E45

    def __init__(self, stream, root_name='root'):
        self.stream = stream
        self.reader = stream
        self.root_name = root_name

    def read_int32(self):
        return struct.unpack('<i', self.reader.read(4))[0]

    def read_int16(self):
        return struct.unpack('<h', self.reader.read(2))[0]

    def read_sbyte(self):
        return struct.unpack('<b', self.reader.read(1))[0]

    def read_bytes(self, n):
        return self.reader.read(n)

    def read_string_till_zero(self):
        chars = []
        while True:
            b = self.reader.read(1)
            if not b or b == b'\x00':
                break
            chars.append(b)
        return b''.join(chars).decode('utf-8')

    def read_dictionary(self):
        dictionary = []
        while True:
            text = self.read_string_till_zero()
            if len(text) == 0:
                break
            dictionary.append(text)
        return dictionary

    def read_string(self, length):
        return self.reader.read(length).decode('utf-8')

    def read_number(self, length):
        if length == 1:
            return str(self.read_sbyte())
        elif length == 2:
            return str(self.read_int16())
        elif length == 4:
            return str(self.read_int32())
        elif length == 8:
            return str(struct.unpack('<q', self.reader.read(8))[0])
        return '0'

    def read_floats(self, n):
        return [struct.unpack('<f', self.reader.read(4))[0] for _ in range(n)]

    def read_base64_as_text(self, length):
        bytes_ = self.reader.read(length)
        # 直接转base64字符串
        import base64
        return base64.b64encode(bytes_).decode('ascii')

    def read_header(self):
        head = self.read_int32()
        if head != self.Packed_Header:
            raise Exception('File is not packed xml')
        self.read_sbyte()  # skip one byte

    def decode(self):
        xDoc = ET.ElementTree()
        xmlroot = ET.Element(self.root_name)
        self.read_header()
        dictionary = self.read_dictionary()
        self.read_element(xmlroot, dictionary)
        return ET.tostring(xmlroot, encoding='utf-8').decode('utf-8')

    def read_element(self, element, dictionary):
        child_count = self.read_int16()
        descriptor = PackedXmlDataDescriptor(self.read_int32())
        elements = []
        for _ in range(child_count):
            name_index = self.read_int16()
            name = dictionary[name_index]
            elements.append(PackedXmlElementDescriptor(name_index, name, self.read_int32()))
        offset = self.read_element_data(element, dictionary, descriptor)
        for elementDescriptor in elements:
            elementName = dictionary[elementDescriptor.name_index]
            child = ET.Element(elementName)
            offset = self.read_element_data(child, dictionary, elementDescriptor, offset)
            element.append(child)

    def read_element_data(self, element, dictionary, descriptor, offset=0):
        lengthInBytes = descriptor.end - offset
        t = descriptor.type
        if t == PackedXmlDataType.Element:
            self.read_element(element, dictionary)
        elif t == PackedXmlDataType.String:
            element.text = self.read_string(lengthInBytes)
        elif t == PackedXmlDataType.Integer:
            element.text = self.read_number(lengthInBytes)
        elif t == PackedXmlDataType.Float:
            floats = self.read_floats(lengthInBytes // 4)
            if len(floats) == 12:
                for i in range(4):
                    row = ET.Element(f'row{i}')
                    row.text = ' '.join(f'{f:.6f}' for f in floats[i*3:(i+1)*3])
                    element.append(row)
            else:
                element.text = ' '.join(f'{f:.6f}' for f in floats)
        elif t == PackedXmlDataType.Boolean:
            if lengthInBytes != 1:
                element.text = 'false'
            else:
                if self.read_sbyte() != 1:
                    raise Exception('Boolean error')
                element.text = 'true'
        elif t == PackedXmlDataType.Base64:
            element.text = self.read_base64_as_text(lengthInBytes)
        else:
            raise Exception(f'Unknown type of element {element.tag}: {t}')
        return descriptor.end

def decode_packedxml_strict(bin_data, root_name='root'):
    reader = PackedXmlReader(io.BytesIO(bin_data), root_name)
    return reader.decode() 