// Exact representable boundaries, duplicate occurrences, tails and pointer/stream churn.
#pragma once
#include <cstdint>
static int b1Fixtures(){
    const int sizes[]={0,1,7,8,9,31,32,33,513};double maximum=0;int empty=0,boundary=0;
    for(int iteration=0;iteration<100;iteration++){
        int n=sizes[iteration%9];std::vector<float> data(size_t(n)*960),q(960,iteration%4==2?16.f:0.f);
        for(int row=5;row<n;row++)for(int j=0;j<960;j++){
            uint32_t h=uint32_t(row)*0x9e3779b9u+uint32_t(j)*0x85ebca6bu;
            h^=h>>16;h*=0x7feb352du;h^=h>>15;
            data[size_t(row)*960+j]=(int(h%15)-7)/1024.f;
        }
        if(n>2)data[2*960]=1.f;
        if(n>3)data[3*960]=std::nextafter(1.f,0.f);
        if(n>4)data[4*960]=std::nextafter(1.f,2.f);
        float radius=iteration%4==0?1.f:iteration%4==3?.125f:0.f;
        Scan slots[2];for(auto& s:slots)s.build(data,n,960);
        if(slots[0].stream==slots[1].stream)throw std::runtime_error("distinct streams");
        std::vector<int> expected;
        std::vector<double> reference(n);
        for(int row=0;row<n;row++){
            double sum=0;for(int j=0;j<960;j++){double v=double(data[size_t(row)*960+j])-double(q[j]);sum+=v*v;}
            reference[row]=sum;if(sum<=double(radius)*radius)expected.push_back(row);
            if(sum==double(radius)*radius)++boundary;
        }
        for(auto& s:slots){
            std::vector<int> ids;std::vector<float> fields;std::vector<double> raw;
            s.range(q.data(),radius,ids,fields,raw);
            if(ids!=expected||fields.size()!=ids.size()||raw.size()!=ids.size())throw std::runtime_error("fixture complete members/order");
            std::vector<float> scores(n);if(n)ck(cudaMemcpy(scores.data(),s.squared,size_t(n)*4,cudaMemcpyDeviceToHost));
            for(int row=0;row<n;row++){
                double error=std::abs(double(scores[row])-reference[row])/std::max(1.,reference[row]);
                if(!std::isfinite(scores[row])||error>5e-5)throw std::runtime_error("fixture all score fields");
                maximum=std::max(maximum,error);
            }
            for(size_t i=0;i<ids.size();i++){
                double target=reference[ids[i]];
                if(raw[i]!=double(scores[ids[i]])||std::abs(double(fields[i])*fields[i]-target)>5e-5*std::max(1.,target))throw std::runtime_error("fixture materialized fields");
            }
            if(ids.empty())++empty;s.release();
        }
    }
    if(!empty||!boundary)throw std::runtime_error("fixture coverage");
    std::cout<<std::setprecision(17)<<"{\"passed\":true,\"iterations\":100,\"stream_slots\":2,\"empty_answers\":"<<empty<<",\"exact_boundary_pairs\":"<<boundary<<",\"max_score_error\":"<<maximum<<"}\n";
    return 0;
}
