#include <ArborX.hpp>
#include <Kokkos_Core.hpp>
#include "bench_io.hpp"
using Exec=Kokkos::Cuda;using Mem=Kokkos::CudaSpace;using Point=ArborX::Point<2,double>;
struct Getter {
 unsigned long long* count;
 template<class V>KOKKOS_FUNCTION auto operator()(V const& v) const {
#if INSTRUMENT
  Kokkos::atomic_add(count,1ull);
#endif
  return v.value;
 }
};
int main(int argc,char**argv){
 assert(argc==11&&std::string(argv[1])=="tloc"&&std::string(argv[5])=="X");
 {std::ofstream pf(std::string(argv[9])+".pid");pf<<getpid()<<'\n';}
 Case c(argv[3],std::stoi(argv[4]),std::stoi(argv[6]));int reps=std::stoi(argv[7]),warm=std::stoi(argv[8]);std::string prefix=argv[9];bool dump=std::stoi(argv[10]);RunLog log(prefix);
 Kokkos::ScopeGuard guard(argc,argv);Exec exec;
 std::ifstream f(argv[2],std::ios::binary);int h[3];f.read((char*)h,12);assert(f&&h[0]==2&&h[1]==c.n&&h[2]==2);std::vector<float> input(size_t(c.n)*2);f.read((char*)input.data(),input.size()*4);assert(f);
 Kokkos::View<Point*,Mem> points("points",c.n);auto hp=Kokkos::create_mirror_view(points);for(int i=0;i<c.n;++i)hp(i)=Point{double(input[2*i]),double(input[2*i+1])};Kokkos::deep_copy(points,hp);
 Kokkos::View<float*[2],Mem> x("float_coordinates",c.n);auto hx=Kokkos::create_mirror_view(x);for(int i=0;i<c.n;++i)for(int j=0;j<2;++j)hx(i,j)=input[2*i+j];Kokkos::deep_copy(x,hx);
 Kokkos::View<unsigned long long*,Mem> counter("getter_calls",2);auto t=WallClock::now();ArborX::BoundingVolumeHierarchy tree(exec,ArborX::Experimental::attach_indices(points),Getter{counter.data()});exec.fence();log.build=millis(t);
 using Value=typename decltype(tree)::value_type;using Predicate=decltype(ArborX::intersects(ArborX::Sphere<2,double>{}));
 t=WallClock::now();Kokkos::View<Predicate*,Mem> preds("predicates",c.nq);Kokkos::View<Predicate*,Kokkos::CudaHostPinnedSpace> hpreds("host_predicates",c.nq);
 Kokkos::View<int*,Mem> qs("qids",c.nq),offsets("offsets",0);Kokkos::View<int*,Kokkos::CudaHostPinnedSpace> hqs("host_qids",c.nq),ho("host_offsets",c.nq+1);
 Kokkos::View<Value*,Mem> values("values",0);Kokkos::View<Hit*,Mem> projected("projected",0);Kokkos::View<Hit*,Kokkos::CudaHostPinnedSpace> host("host_output",0);log.setup=millis(t);
 auto call=[&](bool native){
#if INSTRUMENT
  Kokkos::deep_copy(counter,0ull);
#endif
  Outputs out(c.nq);if(c.radius<0)return out;
  for(int qi=0;qi<c.nq;++qi){int q=c.qs[qi];hqs(qi)=q;hpreds(qi)=ArborX::intersects(ArborX::Sphere<2,double>{Point{double(input[2*q]),double(input[2*q+1])},double(c.radius)});}
  Kokkos::deep_copy(qs,hqs);Kokkos::deep_copy(preds,hpreds);
  tree.query(exec,preds,values,offsets);const int hits=values.extent(0),nq=c.nq;Kokkos::resize(projected,hits);Kokkos::resize(host,hits);
  Kokkos::parallel_for("result_distance_projection",Kokkos::RangePolicy<Exec>(exec,0,hits),KOKKOS_LAMBDA(int i){int lo=0,hi=nq;while(lo+1<hi){int mid=(lo+hi)/2;if(offsets(mid)<=i)lo=mid;else hi=mid;}int id=values(i).index,q=qs(lo);float d=0;if(id!=q){for(int j=0;j<2;++j)d+=pow(x(id,j)-x(q,j),2);d=pow(d,0.5);}projected(i)={id,d};
#if INSTRUMENT
    if(id!=q)Kokkos::atomic_add(counter.data()+1,1ull);
#endif
  });
  Kokkos::deep_copy(ho,offsets);Kokkos::deep_copy(host,projected);exec.fence();
  for(int qi=0;qi<c.nq;++qi)out[qi].assign(host.data()+ho(qi),host.data()+ho(qi+1));
  if(native)dump_output(prefix+".native.bin",out);canonicalize(out);return out;
 };
 run_case(call,c,log,reps,warm,dump);log.finish("X",c);
#if INSTRUMENT
 auto hc=Kokkos::create_mirror_view_and_copy(Kokkos::HostSpace{},counter);std::ofstream wf(prefix+".work.json");wf<<"{\"native_point_predicate_tests\":"<<hc(0)<<",\"output_projection_distances\":"<<hc(1)<<",\"coordinates\":"<<2*(hc(0)+hc(1))<<",\"candidate_primitive_leaves\":"<<hc(0)<<",\"effective_thread_fraction\":null}\n";
#endif
 std::cout<<"PASS native ArborX Q="<<c.nq<<" r="<<c.radius<<" instrument="<<INSTRUMENT<<'\n';
}
