return=0
for test in Test*.py; do
  if ! PYTHONPATH=../src python ${test}; then
    echo "${test} failed!"
    return=1
  fi
done;

if [ ${return} -ne 0 ]; then
  echo "FAIL!"
else
  echo "SUCCESS!"
fi
exit ${return}
