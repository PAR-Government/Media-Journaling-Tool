cd tests
python -m unittest discover
cd algorithms
python -m unittest discover
cd ..
cd batch
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
cd ..
python -m unittest discover -s tests/plugins -p "*Test.py" -v
cd tests
cd segmentation
python -m segmanagetest
cd ..
cd validation
python -m unittest discover
cd ..
cd ..
cd hp_tool
python -m unittest discover
cd ..
