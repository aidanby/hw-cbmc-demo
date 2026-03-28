// 3-client round-robin arbiter.
// Grants are mutually exclusive. When multiple clients request simultaneously,
// the client whose turn it is gets priority. After each grant, the turn advances
// to the next client in round-robin order (0 → 1 → 2 → 0 → ...).
// If the current-turn client is not requesting, skip to the next requesting
// client (still advance turn past the skipped client).
//
// Your task: implement the logic below so all assertions PROVE.
// The module interface and assertions must not be modified.
module arb3(
  input  clk,
  input  reset,
  input  req0, req1, req2,
  output reg grant0, grant1, grant2
);
  reg [1:0] turn;  // 0, 1, or 2

  always @(posedge clk) begin
    if (reset) begin
      grant0 <= 1'b0;
      grant1 <= 1'b0;
      grant2 <= 1'b0;
      turn   <= 2'd0;
    end else begin
      grant0 <= 1'b0;
      grant1 <= 1'b0;
      grant2 <= 1'b0;
      // TODO: implement round-robin grant logic using 'turn'
      // Rules:
      //   - At most one grant per cycle
      //   - If req[turn] is asserted, grant it and advance turn
      //   - If req[turn] is not asserted but another req is, grant the next
      //     requesting client in round-robin order and set turn past it
      //   - If no requests, no grant; turn does not advance
    end
  end

  p_mutex01: assert property (@(posedge clk) !(grant0 && grant1));
  p_mutex02: assert property (@(posedge clk) !(grant0 && grant2));
  p_mutex12: assert property (@(posedge clk) !(grant1 && grant2));
  p_req0_only: assert property (@(posedge clk) req0 && !req1 && !req2 && !reset |=> grant0);
  p_req1_only: assert property (@(posedge clk) !req0 && req1 && !req2 && !reset |=> grant1);
  p_req2_only: assert property (@(posedge clk) !req0 && !req1 && req2 && !reset |=> grant2);
  p_rr_01: assert property (@(posedge clk) req0 && req1 && !req2 && !reset && turn==2'd0 |=> grant0);
  p_rr_12: assert property (@(posedge clk) !req0 && req1 && req2 && !reset && turn==2'd1 |=> grant1);
  p_turn_adv: assert property (@(posedge clk) grant0 && !reset |=> turn == 2'd1);
endmodule
