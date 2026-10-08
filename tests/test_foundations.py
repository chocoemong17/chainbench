"""Independent arithmetic, numerical-state and presentation-timeline contracts."""
import math

import numpy as np
import pytest

from chainbench import foundations as f


@pytest.mark.parametrize('values', [f.VALUES,(1,-2,0,3,-1),(0,1,2,0,4),(.1,.2,.3,.4,.5)])
def test_branched_gradients_match_independent_finite_differences(values):
    def loss(v):
        return ((v[0]*v[1]+v[2]*v[3]*v[4])-4)**2/2
    gradient=[]
    for i in range(5):
        a,b=list(values),list(values)
        a[i]+=1e-6
        b[i]-=1e-6
        gradient.append((loss(a)-loss(b))/2e-6)
    np.testing.assert_allclose(f.gradients(values),gradient,atol=1e-7)


def test_each_training_update_recomputes_gradients_and_improves_this_fixture():
    trace=f.training_trace()
    assert len(trace)==7
    assert trace[1]['y']==pytest.approx(3.433024)
    assert trace[-1]['y']==pytest.approx(3.996455265496761)
    for a,b in zip(trace,trace[1:]):
        np.testing.assert_allclose(b['values'],np.array(a['values'])-.02*np.array(a['gradients']))
        assert b['loss']<a['loss'] and b['distance_to_target']<a['distance_to_target']
    assert f.branched(f.updated(.5))['loss']>f.branched()['loss']
    assert trace[1]['gradients']!=trace[0]['gradients']


@pytest.mark.parametrize('input_kind', ['bars','zero','signed'])
@pytest.mark.parametrize('stride',[1,2])
def test_convolution_against_window_tensor_and_tied_matrix(input_kind,stride):
    data=np.array(f.picture(),dtype=float)
    if input_kind=='zero':
        data[:]=0
    if input_kind=='signed':
        data=(np.arange(63).reshape(7,9)-20)/7
    windows=np.lib.stride_tricks.sliding_window_view(data,(3,3))[::stride,::stride]
    expected=np.maximum(0,np.einsum('rcij,kij->krc',windows,np.array([f.VERTICAL,f.HORIZONTAL])))
    np.testing.assert_allclose(f.first_layer(stride,data.tolist()),expected,atol=1e-12)
    if stride==1:
        matrix=np.array(f.matrix())
        np.testing.assert_allclose(np.maximum(0,matrix@data.ravel()),expected.ravel(),atol=1e-12)
        assert matrix.shape==(70,63) and np.count_nonzero(matrix)==630


def test_second_layer_sums_both_channels_before_relu():
    first=np.array(f.first_layer())
    windows=np.lib.stride_tricks.sliding_window_view(first,(3,3),axis=(1,2))
    weights=np.array([[[[1/9]*3]*3,[[1/18]*3]*3],[[[1/18]*3]*3,[[1/9]*3]*3]])
    expected=np.maximum(0,np.einsum('crsij,kcij->krs',windows,weights))
    np.testing.assert_allclose(f.second_layer(first.tolist()),expected,atol=1e-12)
    np.testing.assert_allclose(f.cnn_values()['scores'],np.array([[1,-.5],[-.5,1]])@expected.mean(axis=(1,2)))


@pytest.mark.parametrize('selection',range(5))
def test_dropout_exact_gates_with_independent_matrix_products(selection):
    m1,m2=f.masks()[selection]
    h1=np.maximum(0,np.array(f.W1)@f.INPUT)*m1
    h2=np.maximum(0,np.array(f.W2)@h1)*m2
    result=f.dropout(m1,m2)
    np.testing.assert_allclose(result['layers'][3],np.array(f.W3)@h2,atol=1e-14)
    assert [len(v) for v in result['layers']]==[3,5,5,2]
    if selection==2:
        assert sum(m1)==0 and result['layers'][3]==[0,0]


def test_prediction_scales_each_hidden_outgoing_matrix():
    a=np.maximum(0,np.array(f.W1)@f.INPUT)
    b=np.maximum(0,(.5*np.array(f.W2))@a)
    expected=(.5*np.array(f.W3))@b
    np.testing.assert_allclose(f.dropout(prediction=True)['layers'][3],expected,atol=1e-14)
    assert sum(w.size for w in map(np.array,[f.W1,f.W2,f.W3]))==50


@pytest.mark.parametrize('slug,duration,chapters',[('backprop',59,12),('cnn',44.72,9),('dropout',30,8)])
def test_contiguous_film_states_and_source_record(slug,duration,chapters):
    record=f.experiment(slug,'a'*40)
    rows=record['timeline']
    assert record['duration']==duration<60
    assert rows[0]['start']==0 and rows[-1]['end']==round(duration*f.FPS)
    assert len(record['chapters'])==chapters
    assert all(a['end']==b['start'] for a,b in zip(rows,rows[1:]))
    assert all(r['end']>r['start'] for r in rows)
    if slug=='backprop':
        assert record['chapters'][-2:]==[40,53]
        assert sum(r['end']-r['start'] for r in rows if r['chapter']==10)==13*f.FPS
        assert [r['iteration'] for r in rows if r.get('phase')=='update']==[2,3,4,5,6]
    if slug=='cnn':
        for chapter,n in [(1,35),(2,35),(3,12)]:
            assert [r['step'] for r in rows if r['chapter']==chapter]==list(range(n))


def test_prior_review_arithmetic_contract_still_passes():
    result=f.verify()
    assert result['backprop']['finite_difference_components']==20
    assert result['backprop']['trace_finite_difference_components']==35
    assert math.isclose(result['dropout']['prediction'][0],-.0375)
