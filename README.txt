Sentinel-2 data masking using SCL data app
By Guy Serbin (guy.serbin@gmail.com) 

This application masks Sentinel-2 data using the Level 2A Scene Classification Layer (SCL) from either specified files 
or directly from extracted Sentinel-2 SAFE data. The application does not support zipped SAFE files at this time. For 
SAFE data, application will extract all relevant bands at 10 m resolution. It can also warp SAFE data to a desired 
projection prior to masking. 

By default, SCL pixels classified as "vegetation", "not_vegetated", and "unclassified" are included as good pixels that
are not to be masked, but these and other classes can be included or excluded via the use of boolean command line 
arguments detailed below.

This application can be run via two methods:

1. Python script. This requires a recent version Python 3, and GDAL (>= 2.1) and Numpy python libraries. GDAL and numpy
	may be installed locally via:
	a. Anaconda Python (www.anaconda.com). After installation, the libraries may be installed from Anaconda Prompt via:
		conda install -c conda-forge gdal numpy
	b. Regular Python via:
		pip install gdal numpy

	Usage:
		Preprocessed data:
			python S2_apply_SCL_mask.py \
				--infile <preprocessed_Sentinel_2_scene> \
				--maskfile <SCL_file> \
				--outpath <path_to_output_folder_or_file>
		
		Unzipped SAFE data:
			python S2_apply_SCL_mask.py \
				--safefile <path_to_SAFE_folder_or_MTD_MSIL2A.xml> \
				--outpath <path_to_output_folder_or_file>
	

2. Docker container. Usage:
		Preprocessed data:
			docker RUN -t \
				--pull missing \
				-v "<local_path_containing_input_data>:/app/data" \
				-v "<local_path_for_output_data>:/app/output" \
				drguyphd/s2_apply_scl_mask \
				python S2_apply_SCL_mask.py \
				--infile <preprocessed_Sentinel_2_scene> \
				--maskfile <SCL_file> \
				--outpath <path_to_output_folder_or_file>
				
		Unzipped SAFE data:
			docker RUN -t \
				--pull missing \
				-v "<local_path_containing_input_data>:/app/data" \
				-v "<local_path_for_output_data>:/app/output" \
				drguyphd/s2_apply_scl_mask \
				python S2_apply_SCL_mask.py \
				--safefile <path_to_SAFE_folder_or_MTD_MSIL2A.xml> \
				--outpath <path_to_output_folder_or_file>

usage: This script masks Sentinel-2 data using the SCL mask file. [-h] [-i INFILE] [-m MASKFILE] [-s SAFEFILE] -o
                                                                  OUTPATH [--vegetation VEGETATION]
                                                                  [--not_vegetated NOT_VEGETATED]
                                                                  [--unclassified UNCLASSIFIED] [--no_data NO_DATA]
                                                                  [--saturated_or_defective SATURATED_OR_DEFECTIVE]
                                                                  [--dark_area_pixels DARK_AREA_PIXELS]
                                                                  [--cloud_shadows CLOUD_SHADOWS] [--water WATER]
                                                                  [--cloud_medium_probability CLOUD_MEDIUM_PROBABILITY]
                                                                  [--cloud_high_probability CLOUD_HIGH_PROBABILITY]
                                                                  [--thin_cirrus THIN_CIRRUS] [--snow SNOW] [--S2TM]
                                                                  [--S2OLI] [--prjstr PRJSTR]

optional arguments:
  -h, --help            show this help message and exit
  -i INFILE, --infile INFILE
                        Full path of image file to be masked.
  -m MASKFILE, --maskfile MASKFILE
                        Full path of SCL mask file.
  -s SAFEFILE, --safefile SAFEFILE
                        Full path of unzipped Sentinel-2 SAFE file. If set, this will override --infile and
                        --maskfile.
  -o OUTPATH, --outpath OUTPATH
                        Masked output file path. If set with a ".tif", extension, will output a file with that name,
                        otherwise will create an output file in that directory.
  --vegetation VEGETATION
                        Include "vegetated" classified pixels. Default = True.
  --not_vegetated NOT_VEGETATED
                        Include "not_vegetated" classified pixels. Default = True.
  --unclassified UNCLASSIFIED
                        Include "unclassified" classified pixels. Default = True.
  --no_data NO_DATA     Include "no_data" classified pixels. Default = False.
  --saturated_or_defective SATURATED_OR_DEFECTIVE
                        Include "saturated_or_defective" classified pixels. Default = False.
  --dark_area_pixels DARK_AREA_PIXELS
                        Include "dark_area_pixels" classified pixels. Default = False.
  --cloud_shadows CLOUD_SHADOWS
                        Include "cloud_shadows" classified pixels. Default = False.
  --water WATER         Include "water" classified pixels. Default = False.
  --cloud_medium_probability CLOUD_MEDIUM_PROBABILITY
                        Include "cloud_medium_probability" classified pixels. Default = False.
  --cloud_high_probability CLOUD_HIGH_PROBABILITY
                        Include "cloud_high_probability" classified pixels. Default = False.
  --thin_cirrus THIN_CIRRUS
                        Include "thin_cirrus" classified pixels. Default = False.
  --snow SNOW           Include "snow" classified pixels. Default = False.
  --S2TM                Process only equivalent Landsat 4-5/ Landsat 7 ETM+ bands.
  --S2OLI               Process only equivalent Landsat 8-9 OLI bands (overrides --S2TM).
  --prjstr PRJSTR       If set, will warp Sentinel-2 SAFE data to the specified EPSG projection, e.g., "EPSG:2172" for
                        Irish Transverse Mercator. This must be formatted "EPSG:XXXXX", where "XXXXX" denotes the EPSG
                        projection code.