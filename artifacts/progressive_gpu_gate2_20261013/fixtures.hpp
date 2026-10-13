// Synthetic coverage is qualification only, never a timing workload.
#pragma once
#include <limits>
static int progressiveFixtures(){
    const int sizes[]={0,1,7,8,9,31,32,33,513,1025};int empty=0,boundary=0;uint64_t rejected[4]{};
    for(int iteration=0;iteration<100;iteration++){
        int n=sizes[iteration%10];std::vector<float> data(size_t(n)*960),q(960,iteration%4==2?16.f:0.f);
        for(int r=10;r<n;r++)for(int j=0;j<960;j++){
            uint32_t h=uint32_t(r)*0x9e3779b9u+uint32_t(j+iteration)*0x85ebca6bu;
            h^=h>>16;h*=0x7feb352du;h^=h>>15;data[size_t(r)*960+j]=(int(h%15)-7)/1024.f;
        }
        if(n>2)data[2*960]=1.f;if(n>3)data[3*960]=std::nextafter(1.f,0.f);
        if(n>4)data[4*960]=std::nextafter(1.f,2.f);
        for(int s=0;s<4;s++)if(n>5+s)data[size_t(5+s)*960+(s==0?127:s==1?255:s==2?511:959)]=2.f;
        if(n>9)data[9*960+959]=.5f;
        if(n>10)data[size_t(n-1)*960]=std::numeric_limits<float>::denorm_min();
        float radius=iteration%4==0?1.f:iteration%4==3?.125f:0.f;
        std::array<std::vector<int>,4> expected;std::vector<double> scores(n);int ends[]={128,256,512,960};
        for(int r=0;r<n;r++){
            double sum=0;int stage=0;bool active=true;
            for(int j=0;j<960;j++){
                double delta=double(data[size_t(r)*960+j])-double(q[j]);double term=delta*delta;sum=sum+term;
                if(j+1==ends[stage]){if(sum<=double(radius)*radius)expected[stage].push_back(r);else if(active){++rejected[stage];active=false;}if(stage<3)++stage;}
            }
            scores[r]=sum;if(sum==double(radius)*radius)++boundary;
        }
        ProgressiveScan slots[2];for(auto& s:slots){s.build(data,n,960);s.audit_mode=4;}
        if(slots[0].stream==slots[1].stream||(n&&slots[0].database==slots[1].database))throw std::runtime_error("independent streams/pointers");
        for(auto& s:slots){
            std::vector<int> ids;std::vector<float> fields;std::vector<double> raw;s.range(q.data(),radius,ids,fields,raw);
            if(ids!=expected[3]||s.last_ids!=expected||ids.size()!=fields.size()||ids.size()!=raw.size())throw std::runtime_error("fixture complete checkpoint IDs");
            for(size_t i=0;i<ids.size();i++){
                double target=scores[ids[i]];float score=float(target);
                if(raw[i]!=double(score)||!std::isfinite(fields[i])||std::abs(double(fields[i])*fields[i]-target)>5e-5*std::max(1.,target))throw std::runtime_error("fixture fields");
            }
            if(ids.empty())++empty;s.release();
        }
    }
    if(!empty||!boundary||!std::all_of(std::begin(rejected),std::end(rejected),[](uint64_t n){return n>0;}))throw std::runtime_error("fixture stage coverage");
    std::cout<<"{\"passed\":true,\"iterations\":100,\"stream_slots\":2,\"empty_answers\":"<<empty<<",\"exact_boundary_pairs\":"<<boundary<<",\"stage_rejects\":[";
    for(int i=0;i<4;i++)std::cout<<(i?",":"")<<rejected[i];std::cout<<"],\"subnormal_cases\":true}\n";return 0;
}
