// 8-bit logical right barrel shifter: shifts input right by 0..7 positions,
// filling vacated bits with 0. Output is combinational.
// The shifter is producing incorrect output for several shift amounts.
module barrel_shift(input [7:0] in, input [2:0] sel, output reg [7:0] out);
  always @(*) begin
    case (sel)
      3'd0: out = 8'b0;              // should be in (no shift)
      3'd1: out = {in[7], in[7:1]}; // should be {1'b0, in[7:1]} (logical, not arithmetic)
      3'd2: out = {2'b00, in[7:2]};
      3'd3: out = {3'b000, in[7:3]};
      3'd4: out = {7'b0000000, in[7]};  // swapped with sel=7: should be {4'b0000, in[7:4]}
      3'd5: out = {5'b00000, in[7:5]};
      3'd6: out = {6'b000000, in[7:6]};
      3'd7: out = {4'b0000, in[7:4]};   // swapped with sel=4: should be {7'b0000000, in[7]}
      default: out = 8'b0;
    endcase
  end

  p_zero:  assert final (sel == 3'd0 -> out == in);
  p_one:   assert final (sel == 3'd1 -> out == {1'b0, in[7:1]});
  p_four:  assert final (sel == 3'd4 -> out == {4'b0000, in[7:4]});
  p_seven: assert final (sel == 3'd7 -> out == {7'b0000000, in[7]});
endmodule
