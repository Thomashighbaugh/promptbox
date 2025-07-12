#!/usr/bin/env bash 
clear 
echo "-----------------------P R O M P T B O X--------------------------------"
echo 
echo
read -p "This will clear the entire virtual environment of the project and the pycache directories. Proceed? [y/n]: " choice; [[ "$choice" != "y" ]] && exit


echo "-------------------Cleaning project build artificats--------------------"
rm -rf .venv  
rm -rf dist 
rm -rvf build  

echo "---------------------Cleaning pycache directories----------------------"
find . -type d -name "__pycache__" | sort | uniq | while read dir; do
    rm -rvf "$dir"
done

echo "--------------------Create Virtual Environment-------------------------"
python -m venv .venv 
source .venv/bin/activate 
echo "Build the Project Then Run It In the Shell" 
pip install -e . 
python -m streamlit run src/promptbox/app.py 

