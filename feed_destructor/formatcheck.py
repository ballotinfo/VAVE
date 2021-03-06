from schema import Schema
from ConfigParser import ConfigParser
import csv
import os

REQUIRED_ELEMENTS = ["source", "election"]
CONFIG_FNAME = "vip.cfg"

class FormatCheck:

	def __init__(self, schema_file, directory=os.getcwd()):

		self.set_schema_props(schema_file)
		self.set_directory(directory)

		self.invalid_files = {}
		self.valid_files = {}
		self.invalid_sections = []
	
	def set_directory(self, directory):
		self.directory = directory
		if not self.directory.endswith("/"):
			self.directory += "/"
		if not os.path.exists(self.directory):
			os.mkdir(self.directory)

	def set_schema_props(self, schema_file):
		
		schema = Schema(schema_file)
		
		self.schema_version = schema.version
		self.simple_elements = schema.get_element_list("complexType", "simpleAddressType")
		self.detail_elements = schema.get_element_list("complexType", "detailAddressType")
		self.element_list = schema.get_element_list("element","vip_object")
		self.elem_fields = self.get_fields(schema, self.element_list)

	def get_fields(self, schema, elem_list):
		
		field_list = {}
		
		for elem_name in elem_list:

			subschema = schema.get_sub_schema(elem_name)
			e_list = []

			if "elements" in subschema:
				for e in subschema["elements"]:
					e_name = e["name"]
					if e["type"] == "simpleAddressType":
						for s_e in self.simple_elements:
							e_list.append(e_name + "_" + s_e)
					elif e["type"] == "detailAddressType":
						for d_e in self.detail_elements:
							e_list.append(e_name + "_" + d_e)
					else:
						e_list.append(e_name)
					if "simpleContent" in e:
						for sc_attr in e["simpleContent"]["attributes"]:
							e_list.append(e_name + "_" + sc_attr["name"])
			if "attributes" in subschema:
				for a in subschema["attributes"]:
					e_list.append(a["name"])
			
			field_list[elem_name] = []
			field_list[elem_name] = e_list

		return field_list

	def missing_files(self):
	
		missing = []

		for r in REQUIRED_ELEMENTS:
			if r not in self.valid_files.values():
				missing.append(r)
		return missing

	def get_valid_files(self):
		return self.valid_files

	def get_invalid_files(self):
		return self.invalid_files

	def validate_files(self):
		
		file_list = os.listdir(self.directory)

		if CONFIG_FNAME in file_list:
			return self.validate_w_config(file_list)
		else:
			return self.validate_wo_config(file_list)

	def validate_wo_config(self, file_list):

		for fname in file_list:

			ename = fname.split(".")[0].lower()

			if ename in self.element_list and (fname.endswith(".txt") or fname.endswith(".csv")):
				
				with open(self.directory + fname) as f:
					
					fdata = csv.DictReader(f)
					if (self.column_check(ename, fdata.fieldnames)):
						self.valid_files[fname] = ename
					else:
						self.invalid_files[fname] = ename

		if len(self.missing_files()) == 0 and len(self.invalid_files) == 0:
			return True
		return False

	def validate_w_config(self, file_list):
		
		config = ConfigParser()
		config.read(self.directory + CONFIG_FNAME)
		sections = config.sections()

		for section in sections:
	
			if section not in self.element_list:
				self.invalid_sections.append(section)
				continue
			if not config.has_option(section, "file_name"):
				self.invalid_sections.append(section)
				continue
			if not config.has_option(section, "header"):
				self.invalid_sections.append(section)
				continue
			
			fname = config.get(section, "file_name")
			header = config.get(section, "header")
			if len(fname) == 0 or len(header) == 0:
				self.invalid_sections.append(section)
				continue
			if fname not in file_list:
				self.invalid_sections.append(section)
				continue

			fieldnames = header.split(",")
			with open(self.directory + fname) as f:

				fdata = csv.reader(f)
				
				try:
					if len(fdata.next()) != len(fieldnames):
						self.invalid_files[fname] = section
						continue
				except:
					self.invalid_files[fname] = section 
					continue
				
				if (self.column_check(section, fieldnames)):
					self.valid_files[fname] = section 
				else:
					self.invalid_files[fname] = section 
		
		if len(self.missing_files()) == 0 and len(self.invalid_files) == 0:
			return True
		return False	

	def column_check(self, ename, header):
	
		for column in header:
			if column not in self.elem_fields[ename]:
				return False
		return True

	def clean_files(self):
	
		file_list = os.listdir(self.directory)

		if CONFIG_FNAME in file_list:
			return self.clean_w_config(file_list)
		else:
			return self.clean_wo_config(file_list)

	def clean_wo_config(self, file_list):
	
		for f in file_list:
			if f in self.invalid_files.keys():
				os.remove(self.directory + f)
			elif f in self.valid_files.keys():
				os.rename(self.directory + f, self.directory + valid_files[f] + ".txt")

	def clean_w_config(self, file_list):
		
		config = ConfigParser()
		config.read(self.directory + CONFIG_FNAME)

		for f in file_list:
			if f in self.invalid_files.keys():
				os.remove(self.directory + f)
			elif f in self.valid_files.keys():
				ename = self.valid_files[f]
				with open(self.directory + ename + "_temp.txt", "w") as fw:
					fw.write(config.get(ename, "header") + "\n")
					with open(self.directory + f, "r") as fr:
						for line in fr:
							fw.write(line)
					os.remove(self.directory + f)
				os.rename(self.directory + ename + "_temp.txt", self.directory + ename + ".txt")
	
	def get_vip_id(self):

		try:
			with open('source.txt', 'rb') as dr:
				r = csv.DictReader(dr)
				row = dr.next()
				return row["vip_id"]
		except:
			pass

	def validate_and_clean(self):
		self.validate_files()
		self.clean_files()

if __name__ == '__main__':
	from urllib import urlopen
	
	fschema = urlopen("https://github.com/votinginfoproject/vip-specification/raw/master/vip_spec_v3.0.xsd")

	fc = FormatCheck(fschema, "../format_check")
	print fc.validate_files()
	print fc.get_valid_files()
	print fc.get_invalid_files()
	print fc.missing_files()
	fc.clean_files()
	
