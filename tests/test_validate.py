import io,os,struct,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validate import pe

def make_pe(machine):
    data=bytearray(256);data[:2]=b'MZ';struct.pack_into('<I',data,0x3c,128)
    data[128:132]=b'PE\0\0';struct.pack_into('<H',data,132,machine);return data
class PeTest(unittest.TestCase):
    def test_real_pe_structure_x64(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'dummy.exe';p.write_bytes(make_pe(0x8664))
            pe(p)
            p.write_bytes(make_pe(0x14c))
            with self.assertRaises(AssertionError):pe(p)
            p.write_bytes(b'MZ'+bytes(128))
            with self.assertRaises(AssertionError):pe(p)
if __name__=='__main__':unittest.main()
