// 2-to-4 decoder: exactly one output bit high based on 2-bit input.
// The decoder is producing incorrect output for some input combinations.
module decoder2to4(input [1:0] in, output reg [3:0] out);
  always @(*) begin
    case (in)
      2'b00: out = 4'b0000;
      2'b01: out = 4'b0110;
      2'b10: out = 4'b0100;
      default: out = 4'b0000;
    endcase
  end

  p_onehot: assert final (out == 4'b0001 || out == 4'b0010 || out == 4'b0100 || out == 4'b1000);
  p_sel0:   assert final (in != 2'b00 || out == 4'b0001);
  p_sel1:   assert final (in != 2'b01 || out == 4'b0010);
  p_sel2:   assert final (in != 2'b10 || out == 4'b0100);
  p_sel3:   assert final (in != 2'b11 || out == 4'b1000);
endmodule
