#!/bin/bash
for file in $(find /tmp -name "*.hepmc3.tree.root"); do
    echo "=== Processing: $file ==="
    ls -lh "$file"
    root -l -b -q -e "
    TFile f(\"$file\");
    TTree* t=(TTree*)f.Get(\"hepmc3_tree\");
    if(!t) { cout << \"No tree found\" << endl; return; }
    t->Draw(\"particles.status\", \"\", \"goff\");
    std::set<int> unique_vals;
    Double_t* values = t->GetV1();
    for(int i = 0; i < t->GetSelectedRows(); i++) {
        unique_vals.insert((int)values[i]);
    }
    cout << \"Unique status codes: \";
    for(auto v : unique_vals) cout << v << \" \";
    cout << endl << \"Count: \" << unique_vals.size() << endl;
    cout << \"========================================\" << endl;
    "
done