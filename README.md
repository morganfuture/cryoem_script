#### 1. script to recenter particles on focused domain for cryoEM 3D refinement and classification
#### usage help:
```bash
python recenter_particle.py -h
```
#### 2. script to strip uid and rename particle image files from cryosparc in batch
#### usage help:
```bash
python rename_file_in_batch.py -h
```
#### 3. script to plot fsc from Relion fsc data
#### usage:
##### open the **plot_fsc_relion.py** and change the fsc filename、resolution、output_figure name

#### 4. script to convert cryosparc cs format into relion star format
#### usage:
```bash
python csparc2relionstar_parser.py -h
```
#### 5. script to convert relion particles.star (good classes) selected from 2D classification to crYOLO-compatible (.cbox or .box) format for model training and particle picking  
#### usage:
```bash
python3 relion2d_to_cryolo.py -h
```
#### 6. mapping particles output from cisTEM to its original input file and restore the lost parameter, such as _rlnMicrographName, _rlnCoordinateX, _rlnCoordinateY. The output particle star file can be used for downstream processing in RELION.
#### usage:
``` bash
python3 cistem2relion_star.py -h
```
#### 7. desymmetrize particle star file after particle Cn symmetry expansion and focused-3D classification. The output particle is C1 and can be used for homogenous or non-uniform refinement further.
#### usage:
``` bash
python desymmetrize_star.py <input.star> <output.star>
```
