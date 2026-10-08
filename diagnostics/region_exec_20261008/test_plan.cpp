#include "region_plan.hpp"
#include <iostream>
#include <numeric>
using namespace rex;
int main(){
 for(int n:{255,256,257}) {
  std::vector<Node> nodes(11);std::vector<int> empty(11,1),ids(n);std::iota(ids.begin(),ids.end(),0);
  nodes[0]={-1,0,n,0,0};empty[0]=0;int pos=0;
  for(int j=1;j<=10;j++){int size=n/10+(j==10?n%10:0);nodes[j]={0,0,size,pos,1};empty[j]=0;pos+=size;}
  auto p=make_plan(nodes,empty,ids,10);if(p.regions.size()!=size_t(n<=256?1:10))return 1;
 }
 for(int n:{255,256,257}){
  std::vector<Node> nodes{{-1,0,n,0,1}};std::vector<int> empty{0},ids(n);std::iota(ids.begin(),ids.end(),0);
  auto p=make_plan(nodes,empty,ids,10);if(p.fallbacks!=(n>256))return 2;
 }
 // Binary chain shapes allow independent exact nonempty-node boundary tests.
 for(int target:{127,128,129}){
  std::vector<Node> nodes(511);std::vector<int> empty(511,1),ids((target+1)/2);std::iota(ids.begin(),ids.end(),0);
  int used=0;std::function<void(int,int,int)> build=[&](int i,int lo,int n){
   empty[i]=0;nodes[i]={0,0,n,lo,n==1};++used;
   if(n>1){int left=n/2;build(2*i+1,lo,left);build(2*i+2,lo+left,n-left);}
  };build(0,0,ids.size());
  // A unary branch introduces exactly the even-node boundary, with an empty sibling.
  if(target==128){int leaf=0;while(!nodes[leaf].is_leaf)leaf=2*leaf+1;
    nodes[leaf].is_leaf=0;nodes[2*leaf+1]=nodes[leaf];nodes[2*leaf+1].is_leaf=1;empty[2*leaf+1]=0;++used;}
  if(used!=target)return 3;auto p=make_plan(nodes,empty,ids,2);
  if((p.regions.size()==1)!=(target<=128))return 4;
 }
 std::cout<<"CPU budgets, maximal partition, canonical coverage, root-leaf/fallback PASS\n";
}
