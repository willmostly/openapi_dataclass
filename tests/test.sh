return=0
for test in Test*.py; do
  if ! PYTHONPATH=../src python ${test}; then
    echo "${test} failed!"
    return=1
  fi
done;

exit ${return}
