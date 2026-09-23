#pragma once
#include <numeric>
#include <vector>
// Independent multiset of original rows. These probes query row zero, never delete
// row zero, and do not insert after rebuild; broader identity semantics are untested.
static std::vector<int> audit_live,audit_sq;
static float audit_radius;
static int audit_step=-1;
static void audit_init(int* info,float* x,float radius){
    if(info[0]!=128||info[1]!=2000||info[2]!=2){std::fprintf(stderr,"AUDIT input outside contract\n");std::exit(24);}
    audit_radius=radius;audit_live.resize(info[1]);std::iota(audit_live.begin(),audit_live.end(),0);audit_sq.resize(info[1]);
    for(int i=0;i<info[1];++i)for(int j=0;j<128;++j){float a=x[i*128+j],b=x[j];if(a<0||a>255||a!=int(a)||b<0||b>255||b!=int(b))std::exit(24);int d=int(a)-int(b);audit_sq[i]+=d*d;}
}
void audit_begin(int flag,int id,int step){
    audit_step=step;
    std::printf("AUDIT_OP,%d,%d,%d\n",step,flag,id);std::fflush(stdout);
    if(flag==0){if(id<0||id>=int(audit_sq.size()))std::exit(24);audit_live.push_back(id);}
    else if(flag==1){if(id==0||id<0||id>=int(audit_live.size()))std::exit(24);audit_live.erase(audit_live.begin()+id);}
    else if(id!=0)std::exit(24);
}
void audit_result(int count){
    int expected=0,excluding_physical_zero=0;
    for(int id:audit_live)if(audit_sq[id]<=double(audit_radius)*audit_radius){++expected;if(id!=0)++excluding_physical_zero;}
    bool pass=count==expected;
    std::printf("AUDIT_COUNT,%d,%d,%d,%d,%s\n",audit_step,count,expected,excluding_physical_zero,pass?"PASS":"FAIL");std::fflush(stdout);
    if(!pass)std::exit(23);
}
