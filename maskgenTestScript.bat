cd tests
python -m unittest discover
cd algorithms
python -m unittest discover
cd ..
cd batch
python -m unittest discover
cd ..
cd external
python -m unittest discover
cd ..
cd ioc
python -m unittest discover
cd ..
cd other_plugins
cd CocoMaskSelector
python -m unittest discover
cd ..
cd ..
cd plugins
python -m unittest discover -s tests/plugins -p "*Test.py" -v 
cd ..
cd segmentation
python -m segmanagetest
cd ..
cd validation
python -m unittest discover
cd ..
