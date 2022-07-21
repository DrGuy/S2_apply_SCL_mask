# -*- coding: utf-8 -*-
"""
Created on Thu Jul 14 18:14:12 2022

@author: guy.serbin@gmail.com
"""

import os, sys, argparse, datetime
try:
    from osgeo import gdal, osr
except:
    import gdal, osr
import numpy as np

def save_masked_file(masked_image_matrix, uint8, outpath, metadata, geoTrans, srs):
    print(f'Creating output file: {outpath}')
    [bands, rows, cols] = masked_image_matrix.shape
    
    # Determine output data type
    if uint8:
        outGDType = gdal.GDT_Byte
    elif masked_image_matrix.dtype == np.uint16: 
        outGDType = gdal.GDT_UInt16
    elif masked_image_matrix.dtype == np.float32:
        outGDType = gdal.GDT_Float32
    
    # Creat output file
    driver = gdal.GetDriverByName('GTiff')
    outraster_ds = driver.Create(outpath, cols, rows, bands, outGDType, options=['COMPRESS=LZW'])
    outraster_ds.SetGeoTransform(geoTrans)
    outraster_ds.SetProjection(srs.ExportToWkt())
    outraster_ds.SetMetadata(metadata)

    if uint8:
        if masked_image_matrix.dtype == np.uint16:
            masked_image_matrix = 255.0 * masked_image_matrix.astype(np.float32) / 10000.0
        else:
            masked_image_matrix = 255.0 * masked_image_matrix
        masked_image_matrix[masked_image_matrix < 0.0] = 0.0
        masked_image_matrix[masked_image_matrix > 255.0] = 255.0

    for i, band in enumerate(masked_image_matrix, start = 1):
        print(f'Writing band {i} of {bands}.')
        outraster_ds.GetRasterBand(i).WriteArray(band)

    print('Output file saved to disk.') 

    # Clear up memory

    outraster_ds = None   
    band = None
    masked_image_matrix = None

def apply_cloud_mask(image_filename, scl_mask_filename, maskVals):
    # open SCL mask file and create mask 
    print(f'Opening SCL mask file: {scl_mask_filename}')
    SCL_ds = gdal.Open(scl_mask_filename)
    prj = SCL_ds.GetProjection()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(SCL_ds.GetProjectionRef())
    geoTrans = SCL_ds.GetGeoTransform()
    scldata = SCL_ds.GetRasterBand(1).ReadAsArray()
    [rows, cols] = scldata.shape
    mask = np.zeros(scldata.shape, dtype = np.byte)
    for maskVal in maskVals:
        mask[scldata == maskVal] = 1
    if not 1 in np.unique(mask):
        print('ERROR: No good mask pixels. Exiting.')
        sys.exit()
    
    # open image file and create masked data array 
    print(f'Opening image mask file: {image_filename}')
    image_ds = gdal.Open(image_filename)
    metadata = image_ds.GetMetadata()
    bands = image_ds.RasterCount
    band = image_ds.GetRasterBand(1).ReadAsArray()
    bandList = [] # Initialize empty band list
    
    for i in range(bands):
        print(f'Masking band {i + 1} of {bands}.')
        band = image_ds.GetRasterBand(i + 1).ReadAsArray() 
        band = band * mask.astype(type(band.dtype))
        bandList.append(band)
    masked_image_matrix = np.stack(bandList)

    print('Masking complete.')   
    # free up memory 
    SCL_ds = None
    scldata = None
    mask = None   
    band = None
    bandList = None
    return masked_image_matrix, metadata, geoTrans, srs

def WarpMGRS(safefile, datasettype, outputdir, *args, **kwargs):
    # This function imports Sentinel-2 L2A SAFE data to 10 a 10m dataset
    # Adapted from IEO 1.5 function od the same name
    prjstr = kwargs.get('prjstr', None) # optional EPSG projection string
    if safefile.endswith('.xml'):
        basename = os.path.basename(os.path.dirname(safefile))
    else:
        basename = os.path.basename(safefile)
    ProductID = basename[:60]
    print(f'Now processing scene: {ProductID} to type {datasettype}.')
    parts = basename.split('_')
    satellite = parts[0]
    datestr = parts[2][:8]
    EPSGstr = 'EPSG_326{}'.format(parts[5][1:3])
    # f = os.path.join(dirname, 'MTD_MSIL2A.xml')
    
    S2dict = {'driver' : 'SENTINEL2',
          '10m' : ['4', '3', '2', '8'],
          '20m' : ['5', '6', '7', '8a', '11', '12', 'SCL'],
          '60m' : ['1', '9'],
          'qbands' : ['SCL'], # ['AOT', 'CLD', 'SCL', 'SNW', 'WVP'],
          'alt' : ['08a'],
          }    
    
    if datasettype == 'Sentinel-2':
        bandlist = ['1', '2', '3', '4', '5', '6', '7', '8', '8a', '9', '11', '12']
    elif datasettype == 'S2OLI':
        bandlist = ['1', '2', '3', '4', '8', '11', '12']
    else:
        bandlist = ['2', '3', '4', '8', '11', '12']
    if safefile.endswith('.zip'):
        safefile = f'/vsizip/{safefile}'
    for sds in ['10m', '20m', '60m']:
        sdsname = f'SENTINEL2_L2A:{safefile}:{sds}:{EPSGstr}'
        print(f'Opening: {sdsname}')
        ds = gdal.Open(sdsname)
        for bandname in S2dict[sds]:
            
            if bandname == '4' and sds == '10m':
                gt = ds.GetGeoTransform()
                extent = [gt[0], gt[3], gt[0] + gt[1] * ds.RasterXSize, gt[3] + gt[5] * ds.RasterYSize]
                xRes = gt[0]
                yRes = -gt[4]
                width, height = ds.RasterXSize, ds.RasterYSize
            bandnum = S2dict[sds].index(bandname) + 1
            if bandname in bandlist:
                if sds == '10m':
                    print(f'Now extracting band {bandname}.')
                else:
                    print(f'Now extracting band {bandname} at 10m spatial resolution.')
                outputfile = os.path.join(outputdir, f'{ProductID}_B{bandname}.tif')
                gdal.Translate(outputfile, ds, xRes = xRes, yRes = yRes, resampleAlg = "bilinear", bandList = [bandnum], format = 'GTiff', noData = 0, width = width, height = height)
            elif bandname == 'SCL':
                SCLfile = os.path.join(outputdir, f'{ProductID}_SCL.tif')
                gdal.Translate(SCLfile, ds, xRes = xRes, yRes = yRes, resampleAlg = "nearest", bandList = [bandnum + 2], format = 'GTiff', noData = 0, width = width, height = height)
    srlist = []
    out_vrt = os.path.join(outputdir, '{}.vrt'.format(ProductID))  
    if not os.path.isfile(out_vrt):
        
        for band in bandlist:
            fb = os.path.join(outputdir, f'{ProductID}_B{band}.tif')
            
            srlist.append(fb)
    print('Stacking bands into a VRT.')
    gdal.BuildVRT(out_vrt, srlist, separate = True)
    if prjstr:  
        projacronym = prjstr.split(':')[1]
        projdir = os.path.join(outputdir, projacronym)
        if not os.path.isdir(projdir):
            os.makedirs(projdir)
        print(f'Bands stacked. Warping to {prjstr}.')    
        outputfile = os.path.join(projdir, f'{ProductID}.tif')
        outSCLfile = os.path.join(projdir, f'{ProductID}_SCL.tif')
        gdal.Warp(outputfile, 
                  out_vrt, #)options = options)
                  format = 'GTiff', 
                  dstSRS = prjstr,
                  resampleAlg = 'bilinear')
        print(f'Bands warped to {prjstr}.')
        print(f'Warping SCL layer to {prjstr}')
        gdal.Warp(outSCLfile, 
                  SCLfile, #)options = options)
                  format = 'GTiff', 
                  dstSRS = prjstr,
                  resampleAlg = 'nearest')
    else:
        outputfile = out_vrt
        outSCLfile = SCLfile
    return outputfile, outSCLfile, datestr

def main(infile = None, maskfile = None, safefile = None, outpath = None, \
        vegetation = True, not_vegetated = True, unclassified = True, \
        no_data = False, saturated_or_defective = False, dark_area_pixels = False, \
        cloud_shadows = False, water = False, cloud_medium_probability = False, \
        cloud_high_probability = False, thin_cirrus = False, snow = False, \
        datasettype = 'Sentinel-2', prjstr = None, uint8 = True):
    startTime = datetime.datetime.now()
    
    if outpath.endswith('.tif'):
        outdir = os.path.dirname(outpath)
    else:
        outdir = outpath
    if not os.path.isdir(outdir):
        print(f'Creating output directory: {outdir}')
        os.mkdir(outdir)
    
    if safefile:
        if safefile.endswith('.zip'):
            print('ERROR: Zipped SAFE files are not yet supported. Please unzip first. Exiting.')
            sys.exit()
        if os.path.isdir(safefile):
            root, dirs, files = os.walk(safefile)
            for name in files:
                if name == 'MTD_MSIL2A.xml' or name.endswith('.zip'):
                    safefile = os.path.join(root, name)
                    if name == 'MTD_MSIL2A.xml':
                        ProductID = os.path.basename(root)[:60]
                    else:
                        ProductID = name[:60]
                    parts = ProductID.split('_')
                    EPSGstr = f'EPSG_326{parts[5][1:3]}'
                    break
        if os.path.isfile(safefile):
            
            infile, maskfile, datestr = WarpMGRS(safefile, datasettype, outdir, prjstr = prjstr)
            if not outpath.endswith('.tif'):
                outpath = os.path.join(outdir, f'{os.path.basename(infile)[:-4]}_masked.tif')
    elif infile and maskfile:
        if os.path.isfile(infile) and os.path.isfile(maskfile):
            if not outpath.endswith('.tif'):
                basename = os.path.basename(infile)[:-4]
                outpath = os.path.join(outdir, f'{basename}_masked.tif')
                print(f'Output file will be saved to: {outpath}')
                
    else:
        print('ERROR: if --safefile path is not set, then both --infile and --maskfile must be. Please check command line arguments. Exiting.')
        sys.exit()
    
    
    classes = [no_data, saturated_or_defective, dark_area_pixels, cloud_shadows,\
               vegetation, not_vegetated, water, unclassified, cloud_medium_probability,\
               cloud_high_probability, thin_cirrus, snow]
    classnames = 'no_data,saturated_or_defective,dark_area_pixels,cloud_shadows,vegetation,not_vegetated,water,unclassified,cloud_medium_probability,cloud_high_probability,thin_cirrus,snow'
    classnames = classnames.split(',')
    maskVals = [] # list containing values for pixels to include in final product
    
    # Iterate through classes. If value == True, append to maskVals
    for i in range(len(classes)):
        if classes[i]:
            print(f'Adding class to good pixel mask: {classnames[i]}')
            maskVals.append(i)
    masked_image_matrix, metadata, geoTrans, srs = apply_cloud_mask(infile, maskfile, maskVals)
    [bands, rows, cols] = masked_image_matrix.shape
    print(f'Masked image matrix dimensions: {bands} bands, {rows} rows, {cols} columns.')
    save_masked_file(masked_image_matrix, uint8, outpath, metadata, geoTrans, srs)

    executionTime = round((datetime.datetime.now() - startTime).seconds, 2)
    print(f'Total time: {executionTime} seconds')
    print('Processing complete.')

if __name__ == '__main__':
    # Parse the expected command line arguments
    parser = argparse.ArgumentParser('This script masks Sentinel-2 data using the SCL mask file.')
    parser.add_argument('-i', '--infile', default = None, type = str, help = 'Full path of image file to be masked.')
    parser.add_argument('-m', '--maskfile', default = None, type = str, help = 'Full path of SCL mask file.')
    parser.add_argument('-s', '--safefile', default = None, type = str, help = 'Full path of unzipped Sentinel-2 SAFE file. If set, this will override --infile and --maskfile.')
    parser.add_argument('-o', '--outpath', default = None, required = True, type = str, help = 'Masked output file path. If set with a ".tif", extension, will output a file with that name, otherwise will create an output file in that directory.')
    parser.add_argument('--vegetation', default = True, type = bool, help = 'Include "vegetated" classified pixels. Default = True.')
    parser.add_argument('--not_vegetated', default = True, type = bool, help = 'Include "not_vegetated" classified pixels. Default = True.')
    parser.add_argument('--unclassified', default = True, type = bool, help = 'Include "unclassified" classified pixels. Default = True.')
    parser.add_argument('--no_data', default = False, type = bool, help = 'Include "no_data" classified pixels. Default = False.')
    parser.add_argument('--saturated_or_defective', default = False, type = bool, help = 'Include "saturated_or_defective" classified pixels. Default = False.')
    parser.add_argument('--dark_area_pixels', default = False, type = bool, help = 'Include "dark_area_pixels" classified pixels. Default = False.')
    parser.add_argument('--cloud_shadows', default = False, type = bool, help = 'Include "cloud_shadows" classified pixels. Default = False.')
    parser.add_argument('--water', default = False, type = bool, help = 'Include "water" classified pixels. Default = False.')
    parser.add_argument('--cloud_medium_probability', default = False, type = bool, help = 'Include "cloud_medium_probability" classified pixels. Default = False.')
    parser.add_argument('--cloud_high_probability', default = False, type = bool, help = 'Include "cloud_high_probability" classified pixels. Default = False.')
    parser.add_argument('--thin_cirrus', default = False, type = bool, help = 'Include "thin_cirrus" classified pixels. Default = False.')
    parser.add_argument('--snow', default = False, type = bool, help = 'Include "snow" classified pixels. Default = False.')
    parser.add_argument('--S2TM', action = 'store_true', help = 'Process only equivalent Landsat 4-5/ Landsat 7 ETM+ bands.')
    parser.add_argument('--S2OLI', action = 'store_true', help = 'Process only equivalent Landsat 8-9 OLI bands (overrides --S2TM).')
    parser.add_argument('--prjstr', default = None, type = str, help = 'If set, will warp Sentinel-2 SAFE data to the specified EPSG projection, e.g., "EPSG:2172" for Irish Transverse Mercator. This must be formatted "EPSG:XXXXX", where "XXXXX" denotes the EPSG projection code.')
    parser.add_argument('--uint8', default = True, type = bool, help = 'Save output as unsigned 8-bit (byte) data. Default = True.')
    args = parser.parse_args()
    
    if args.S2OLI:
        datasettype = 'S2OLI'
    elif args.S2TM:
        datasettype = 'S2TM'
    else:
        datasettype = 'Sentinel-2'
 
    # Pass the parsed arguments to mainline processing   
    main(args.infile, args.maskfile, args.safefile, args.outpath, \
        args.vegetation, args.not_vegetated, args.unclassified, args.no_data, args.saturated_or_defective, \
        args.dark_area_pixels, args.cloud_shadows, args.water, args.cloud_medium_probability, \
        args.cloud_high_probability, args.thin_cirrus, args.snow, datasettype, args.prjstr, args.uint8)